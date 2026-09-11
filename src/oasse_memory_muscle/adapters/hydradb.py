"""HydraDB API v2 transport. Queued ingestion is not proof of indexing.

Wire contract: https://pypi.org/project/hydradb-sdk/ (API version 2).
Uses standard-library HTTP only. No installation, provisioning, or retry loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from typing import TYPE_CHECKING, Any, Mapping
from urllib import error, request
from urllib.parse import urlsplit
import uuid

if TYPE_CHECKING:
    from ..contracts import LearningEvent


class HydraDBError(RuntimeError):
    """Transport or protocol failure; never an empty successful retrieval."""


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class HydraDBResponse:
    status_code: int
    body: dict[str, Any]
    request_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"status_code": self.status_code, "request_id": self.request_id, "body": self.body}


@dataclass(frozen=True)
class HydraDBAdapter:
    api_key: str = field(repr=False)
    database: str = "oasse_aws_hackathon"
    collection: str = "default"
    base_url: str = "https://api.hydradb.com"
    timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        for name in ("api_key", "database", "collection"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or "\r" in value or "\n" in value:
                raise ValueError(f"HydraDB {name} must be nonempty and single-line")
        url = urlsplit(self.base_url)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.path not in ("", "/")):
            raise ValueError("HydraDB base_url must be an HTTPS origin without credentials")
        if (isinstance(self.timeout_seconds, bool)
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0):
            raise ValueError("HydraDB timeout_seconds must be finite and positive")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> HydraDBAdapter:
        values = os.environ if env is None else env
        key = values.get("HYDRADB_API_KEY") or values.get("HYDRA_DB_API_KEY")
        if not key:
            raise ValueError("Set HYDRADB_API_KEY or HYDRA_DB_API_KEY in the local environment")
        return cls(
            api_key=key,
            database=values.get("HYDRADB_DATABASE") or values.get("HYDRADB_TENANT_ID") or "oasse_aws_hackathon",
            collection=values.get("HYDRADB_COLLECTION") or "default",
            base_url=values.get("HYDRADB_BASE_URL") or "https://api.hydradb.com",
        )

    def _post(self, path: str, body: bytes, content_type: str) -> HydraDBResponse:
        req = request.Request(
            self.base_url.rstrip("/") + path, data=body, method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "API-Version": "2",
                     "Accept": "application/json", "Content-Type": content_type},
        )
        # Do not forward bearer credentials to redirect targets or retry writes.
        opener = request.build_opener(_NoRedirect())
        try:
            with opener.open(req, timeout=self.timeout_seconds) as response:
                status = response.status
                raw = response.read(2_097_153)
                request_id = response.headers.get("x-request-id")
        except error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise HydraDBError(f"HydraDB {path}: HTTP {status}; no retry performed") from None
        except (error.URLError, OSError, TimeoutError):
            raise HydraDBError(f"HydraDB {path}: transport failure; no retry performed") from None
        if status not in (200, 202):
            raise HydraDBError(f"HydraDB {path}: unexpected HTTP {status}")
        if len(raw) > 2_097_152:
            raise HydraDBError(f"HydraDB {path}: response exceeds 2 MiB")
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError):
            raise HydraDBError(f"HydraDB {path}: response is not valid JSON") from None
        if not isinstance(payload, dict) or payload.get("error") or payload.get("success") is False:
            raise HydraDBError(f"HydraDB {path}: malformed or error response")
        return HydraDBResponse(status, payload, request_id)

    def ingest_memory(self, text: str, *, record_id: str | None = None) -> HydraDBResponse:
        """Submit one memory; return the actual acknowledgement without claiming indexing."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("HydraDB memory text must be nonempty")
        memory: dict[str, str] = {"text": text}
        if record_id is not None:
            if not isinstance(record_id, str) or not record_id.strip():
                raise ValueError("HydraDB record_id must be nonempty")
            memory["id"] = record_id
        fields = {"database": self.database, "collection": self.collection,
                  "type": "memory", "upsert": "false",
                  "memories": json.dumps([memory], ensure_ascii=False, allow_nan=False)}
        boundary = "oasse-hydra-" + uuid.uuid4().hex
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
            for name, value in fields.items()
        ]
        parts.append(f"--{boundary}--\r\n".encode())
        return self._post("/context/ingest", b"".join(parts), f"multipart/form-data; boundary={boundary}")

    def query(self, text: str, *, source_ids: tuple[str, ...] | None = None) -> HydraDBResponse:
        """Return provider response intact; never widen an explicit source-ID scope."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("HydraDB query must be nonempty")
        payload: dict[str, Any] = {
            "database": self.database, "collections": [self.collection],
            "type": "memory", "query": text, "query_by": "hybrid", "mode": "auto",
            "max_results": 5, "graph_context": True,
        }
        if source_ids is not None:
            if (not isinstance(source_ids, (tuple, list)) or not source_ids
                    or any(not isinstance(item, str) or not item.strip() for item in source_ids)):
                raise ValueError("source_ids must be a nonempty sequence of nonempty strings")
            payload["ids"] = list(source_ids)
        response = self._post("/query", json.dumps(payload, allow_nan=False).encode(), "application/json")
        if response.status_code != 200:
            raise HydraDBError("HydraDB query did not return HTTP 200")
        return response

    def store_learning_event(self, event: LearningEvent) -> str:
        """Return a JSON acknowledgement, not an indexing or execution receipt."""
        text = json.dumps(event.canonical_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False)
        result = self.ingest_memory(text, record_id=event.event_id)
        return json.dumps(result.as_dict(), sort_keys=True, allow_nan=False)

    def related_context(self, failure_signature: str) -> list[dict[str, Any]]:
        response = self.query(failure_signature)
        data = response.body.get("data")
        chunks = data.get("chunks") if isinstance(data, dict) else None
        if not isinstance(chunks, list) or any(not isinstance(chunk, dict) for chunk in chunks):
            raise HydraDBError("HydraDB response lacks the documented data.chunks list; inspect query().body")
        return chunks
