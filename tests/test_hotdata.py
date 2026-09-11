import csv
import io
import json
from urllib import error

import pytest

from oasse_memory_muscle.adapters.hotdata import HotdataAdapter, HotdataError, HotdataPending, _NoRedirect


def adapter(**kwargs):
    values = dict(api_key="test-secret", workspace_id="worktest123", database_id="dbidtest123")
    values.update(kwargs)
    return HotdataAdapter(**values)


def provider(monkeypatch, result, status=200):
    calls = []

    class Response:
        def __init__(self):
            self.status = status
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            value = result if isinstance(result, bytes) else json.dumps(result).encode()
            return value[:size]

    class Opener:
        def open(self, req, timeout):
            calls.append((req, timeout))
            if isinstance(result, Exception):
                raise result
            return Response()

    monkeypatch.setattr("oasse_memory_muscle.adapters.hotdata.request.build_opener", lambda *_: Opener())
    return calls


def ack(table="test_table", count=1):
    return dict(row_count=count, schema_name="public", table_name=table, connection_id="conn-test", arrow_schema_json="{}")


def query_result():
    return dict(columns=["record_id", "synthetic"], rows=[["r1", True]], row_count=1, preview_row_count=1,
                truncated=False, query_run_id="qrun1", result_id="result1")


def test_load_headers_csv_and_non_destructive_mode(monkeypatch):
    calls = provider(monkeypatch, ack())
    rows = [{"learning": 'comma, quote " and\nnewline', "synthetic": True}]
    assert adapter().load_rows("test_table", rows)["row_count"] == 1
    req, timeout = calls[0]
    assert req.full_url == "https://api.hotdata.dev/v1/databases/dbidtest123/schemas/public/tables/test_table/loads"
    assert req.get_header("Authorization") == "Bearer test-secret"
    assert req.get_header("X-workspace-id") == "worktest123"
    body = json.loads(req.data)
    assert body["mode"] == "append" and body["async"] is False
    assert list(csv.DictReader(io.StringIO(body["data"]))) == [{"learning": rows[0]["learning"], "synthetic": "true"}]
    assert timeout == 30
    assert "test-secret" not in repr(adapter())


def test_idempotency_stable_and_changes_with_data_or_batch(monkeypatch):
    calls = provider(monkeypatch, ack())
    a = adapter()
    for data, batch in [(1, "a"), (1, "a"), (2, "a"), (1, "b")]:
        a.load_rows("test_table", [{"value": data}], batch_id=batch)
    keys = [json.loads(req.data)["idempotency_key"] for req, _ in calls]
    assert keys[0] == keys[1]
    assert len(set(keys)) == 3


def test_run_scoping_does_not_mutate_rows(monkeypatch):
    a = adapter()
    calls = provider(monkeypatch, ack(a.table_for_run("run1")))
    rows = [{"test_status": "failed"}]
    assert a.load("run1", rows) is None
    assert rows == [{"test_status": "failed"}]
    assert a.qualified_table("run1").startswith("default.public.oasse_run_")
    assert a.table_for_run("run1") != a.table_for_run("run2")
    assert "run1" in json.loads(calls[0][0].data)["data"]


def test_query_database_scope_and_metadata(monkeypatch):
    calls = provider(monkeypatch, query_result())
    a = adapter()
    assert a.query("SELECT * FROM default.public.test_table") == [{"record_id": "r1", "synthetic": True}]
    req = calls[0][0]
    assert req.full_url.endswith("/v1/query")
    assert req.get_header("X-database-id") is None
    assert json.loads(req.data)["database_id"] == "dbidtest123"
    assert a.query_raw("SELECT 1")["query_run_id"] == "qrun1"


@pytest.mark.parametrize("changes", [{"truncated": True}, {"columns": ["x", "x"]}, {"rows": [[1]]},
                                      {"rows": [{}]}, {"preview_row_count": 8}, {"preview_row_count": True},
                                      {"truncated": None}, {"columns": "bad"}])
def test_rejects_partial_or_malformed_query(monkeypatch, changes):
    result = {**query_result(), **changes}
    provider(monkeypatch, result)
    with pytest.raises(HotdataError):
        adapter().query("SELECT 1")


@pytest.mark.parametrize("result", [{"row_count": 0}, {"row_count": True}, {"table_name": "other"}, {"schema_name": "other"}])
def test_rejects_inconsistent_load_ack(monkeypatch, result):
    provider(monkeypatch, {**ack(), **result})
    with pytest.raises(HotdataError):
        adapter().load_rows("test_table", [{"x": 1}])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {"nested": True}, [1]])
def test_rejects_non_scalar_or_nonfinite_rows(value):
    with pytest.raises(ValueError):
        adapter().load_rows("test_table", [{"value": value}])


@pytest.mark.parametrize("changes", [{"api_key": ""}, {"api_key": "abc\r\nInjected:x"}, {"workspace_id": "bad"},
                                      {"database_id": "hackathon-test"}, {"schema": "../x"},
                                      {"timeout_seconds": -1}, {"timeout_seconds": float("nan")}, {"timeout_seconds": True}])
def test_rejects_bad_configuration(changes):
    with pytest.raises(ValueError):
        adapter(**changes)


def test_bad_rows_and_names():
    a = adapter()
    for table, rows in [("../x", [{"x": 1}]), ("x", []), ("x", [{"x": 1}, {"y": 2}]), ("x", [{"bad key": 1}])]:
        with pytest.raises(ValueError):
            a.load_rows(table, rows)
    with pytest.raises(ValueError):
        a.load("run1", [{"run_id": "other"}])
    with pytest.raises(ValueError, match="2 MiB"):
        a.load_rows("test_table", [{"x": "x" * (2 * 1024 * 1024)}])


@pytest.mark.parametrize("status", [202, 204, 302])
def test_non_sync_status_never_success(monkeypatch, status):
    provider(monkeypatch, {"status": "pending"}, status)
    with pytest.raises(HotdataPending if status == 202 else HotdataError):
        adapter().query_raw("SELECT 1")


@pytest.mark.parametrize("result", [b"not json", [], {"error": "bad"}])
def test_invalid_response(monkeypatch, result):
    provider(monkeypatch, result)
    with pytest.raises(HotdataError):
        adapter().query_raw("SELECT 1")


def test_http_error_no_secret_or_retry(monkeypatch):
    err = error.HTTPError("https://api.hotdata.dev", 429, "test-secret", {}, io.BytesIO(b"test-secret"))
    calls = provider(monkeypatch, err)
    with pytest.raises(HotdataError, match="HTTP 429") as caught:
        adapter().query_raw("SELECT 1")
    assert "test-secret" not in str(caught.value) and len(calls) == 1


def test_timeout_no_retry(monkeypatch):
    calls = provider(monkeypatch, TimeoutError("test-secret"))
    with pytest.raises(HotdataError, match="outcome may be unknown"):
        adapter().query_raw("SELECT 1")
    assert len(calls) == 1


def test_redirect_refused():
    with pytest.raises(HotdataError, match="not forwarded"):
        _NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example")
