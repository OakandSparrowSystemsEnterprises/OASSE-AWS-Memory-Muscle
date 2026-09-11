"""Offline transport fixtures, not claims of live sponsor verification."""
from email import policy
from email.parser import BytesParser
import io
import json
from types import SimpleNamespace
from urllib import error

import pytest

from oasse_memory_muscle.adapters.hydradb import HydraDBAdapter, HydraDBError, _NoRedirect


class Reply(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body if isinstance(body, bytes) else json.dumps(body).encode())
        self.status = status
        self.headers = {"x-request-id": "fixture-request"}


def transport(monkeypatch, body, status=200):
    calls = []

    def open_request(req, timeout):
        calls.append((req, timeout))
        return Reply(body, status)

    monkeypatch.setattr("oasse_memory_muscle.adapters.hydradb.request.build_opener",
                        lambda *args: SimpleNamespace(open=open_request))
    return calls


def form_fields(req):
    prefix = f"Content-Type: {req.get_header('Content-type')}\r\nMIME-Version: 1.0\r\n\r\n".encode()
    msg = BytesParser(policy=policy.default).parsebytes(prefix + req.data)
    return {part.get_param("name", header="content-disposition"): part.get_payload(decode=True).decode()
            for part in msg.iter_parts()}


def test_ingest_one_memory_v2_scope_and_acknowledgement(monkeypatch):
    body = {"data": {"queued": 1, "failed": 0}, "meta": {"fixture": True}}
    calls = transport(monkeypatch, body, 202)
    reply = HydraDBAdapter("test-secret").ingest_memory("cap backoff", record_id="fixture-1")
    req, timeout = calls[0]
    assert len(calls) == 1
    assert req.full_url == "https://api.hydradb.com/context/ingest"
    assert req.get_method() == "POST"
    assert req.get_header("Api-version") == "2"
    assert req.get_header("Authorization") == "Bearer test-secret"
    assert timeout == 20
    fields = form_fields(req)
    assert fields["database"] == "oasse_aws_hackathon"
    assert fields["collection"] == "default"
    assert fields["type"] == "memory"
    assert fields["upsert"] == "false"
    assert json.loads(fields["memories"]) == [{"text": "cap backoff", "id": "fixture-1"}]
    assert reply.as_dict() == {"status_code": 202, "request_id": "fixture-request", "body": body}


def test_query_preserves_source_binding_and_payload(monkeypatch):
    body = {"data": {"chunks": [{"id": "fixture-1_chunk_0000", "text": "cap backoff"}]}}
    calls = transport(monkeypatch, body)
    result = HydraDBAdapter("secret").query("retry-backoff-cap", source_ids=("fixture-1",))
    req, _ = calls[0]
    assert req.full_url == "https://api.hydradb.com/query"
    payload = json.loads(req.data)
    assert payload["database"] == "oasse_aws_hackathon"
    assert payload["collections"] == ["default"]
    assert payload["ids"] == ["fixture-1"]
    assert payload["type"] == "memory"
    assert payload["graph_context"] is True
    assert result.body == body
    assert len(calls) == 1


@pytest.mark.parametrize("ids", [(), [], ("",), "fixture-1"])
def test_bad_source_scope_never_widens(ids):
    with pytest.raises(ValueError):
        HydraDBAdapter("secret").query("test", source_ids=ids)


def test_port_returns_actual_chunks(monkeypatch):
    chunks = [{"id": "fixture-1", "text": "lesson", "score": 0.5}]
    transport(monkeypatch, {"data": {"chunks": chunks}})
    assert HydraDBAdapter("secret").related_context("signature") == chunks


def test_empty_success_is_distinct_from_broken_response(monkeypatch):
    transport(monkeypatch, {"data": {"chunks": []}})
    assert HydraDBAdapter("secret").related_context("signature") == []
    transport(monkeypatch, {"unexpected": "shape"})
    with pytest.raises(HydraDBError, match="data.chunks"):
        HydraDBAdapter("secret").related_context("signature")


def test_learning_event_preserves_canonical_content_and_queued_state(monkeypatch):
    calls = transport(monkeypatch, {"data": {"queued": 1, "failed": 0}}, 202)
    canonical = {"event_id": "event-1", "failure_signature": "retry-backoff-cap", "success": False}
    event = SimpleNamespace(event_id="event-1", canonical_dict=lambda: canonical)
    ack = json.loads(HydraDBAdapter("secret").store_learning_event(event))
    memory = json.loads(form_fields(calls[0][0])["memories"])[0]
    assert json.loads(memory["text"]) == canonical
    assert memory["id"] == "event-1"
    assert ack["status_code"] == 202
    assert "indexed" not in ack


@pytest.mark.parametrize("body", [b"not json", [], {"error": "bad"}, {"success": False}])
def test_invalid_json_or_error_response_fails(monkeypatch, body):
    transport(monkeypatch, body)
    with pytest.raises(HydraDBError):
        HydraDBAdapter("secret").query("test")


def test_http_failure_has_no_retry_or_secret_echo(monkeypatch):
    calls = []
    def fail(req, timeout):
        calls.append(req)
        raise error.HTTPError(req.full_url, 401, "secret-value", {}, io.BytesIO(b"secret-value"))
    monkeypatch.setattr("oasse_memory_muscle.adapters.hydradb.request.build_opener",
                        lambda *args: SimpleNamespace(open=fail))
    with pytest.raises(HydraDBError, match="HTTP 401") as caught:
        HydraDBAdapter("secret-value").ingest_memory("test")
    assert "secret-value" not in str(caught.value)
    assert len(calls) == 1


def test_timeout_has_no_retry(monkeypatch):
    def fail(req, timeout):
        raise TimeoutError("private detail")
    monkeypatch.setattr("oasse_memory_muscle.adapters.hydradb.request.build_opener",
                        lambda *args: SimpleNamespace(open=fail))
    with pytest.raises(HydraDBError, match="transport failure"):
        HydraDBAdapter("secret").query("test")


def test_secret_is_not_in_repr_and_existing_env_names_work():
    adapter = HydraDBAdapter.from_env({"HYDRA_DB_API_KEY": "private-token", "HYDRADB_TENANT_ID": "event-db"})
    assert "private-token" not in repr(adapter)
    assert adapter.database == "event-db"
    assert adapter.collection == "default"
    assert HydraDBAdapter.from_env({"HYDRADB_API_KEY": "key", "HYDRADB_COLLECTION": "other"}).collection == "other"
    with pytest.raises(ValueError, match="Set HYDRADB_API_KEY"):
        HydraDBAdapter.from_env({})


@pytest.mark.parametrize("url", ["http://api.hydradb.com", "https://user:secret@example.com", "https://example.com/?key=secret"])
def test_unsafe_origin_is_rejected(url):
    with pytest.raises(ValueError):
        HydraDBAdapter("secret", base_url=url)


def test_redirects_do_not_forward_bearer():
    assert _NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example") is None


def test_async_response_is_not_successful_query(monkeypatch):
    transport(monkeypatch, {"data": {}}, 202)
    with pytest.raises(HydraDBError, match="HTTP 200"):
        HydraDBAdapter("secret").query("test")
