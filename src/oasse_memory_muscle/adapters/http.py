from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class HttpCallError(RuntimeError):
    pass


@dataclass(frozen=True)
class JsonHttpClient:
    base_url: str
    token: str | None = None
    timeout_seconds: float = 20.0

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        merged_headers = {"Accept": "application/json"}
        if payload is not None:
            merged_headers["Content-Type"] = "application/json"
        if self.token:
            merged_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            merged_headers.update(headers)

        req = request.Request(self._url(path), data=body, method=method.upper(), headers=merged_headers)
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HttpCallError(f"HTTP {exc.code} for {method.upper()} {path}: {detail}") from exc
        except error.URLError as exc:
            raise HttpCallError(f"transport failure for {method.upper()} {path}: {exc.reason}") from exc
