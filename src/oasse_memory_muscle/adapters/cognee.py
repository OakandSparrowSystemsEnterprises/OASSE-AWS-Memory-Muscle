from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from .http import HttpCallError, JsonHttpClient


@dataclass(frozen=True)
class CogneeAdapter:
    base_url: str
    api_key: str
    dataset: str
    timeout_seconds: float = 30.0

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def recall(self, query: str) -> list[str]:
        client = JsonHttpClient(self.base_url, timeout_seconds=self.timeout_seconds)
        result = client.request_json(
            "POST",
            "/api/v1/recall",
            payload={
                "query": query,
                "datasets": [self.dataset],
                "searchType": "GRAPH_COMPLETION",
                "topK": 10,
                "onlyContext": False,
                "verbose": False,
            },
            headers=self._headers(),
        )
        if not isinstance(result, list):
            return [json.dumps(result, sort_keys=True)]
        values: list[str] = []
        for item in result:
            if isinstance(item, str):
                values.append(item)
            elif isinstance(item, dict):
                values.append(str(item.get("answer") or item.get("context") or json.dumps(item, sort_keys=True)))
            else:
                values.append(str(item))
        return values

    def remember(self, text: str) -> str:
        boundary = f"----oasse-{uuid.uuid4().hex}"
        filename = "learning-event.txt"
        chunks = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"datasetName\"\r\n\r\n{self.dataset}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"run_in_background\"\r\n\r\nfalse\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"data\"; filename=\"{filename}\"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n".encode(),
            text.encode("utf-8"),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        body = b"".join(chunks)
        headers = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Api-Key": self.api_key,
        }
        req = request.Request(
            f"{self.base_url.rstrip('/')}/api/v1/remember",
            data=body,
            method="POST",
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return raw or "ok"
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HttpCallError(f"Cognee remember failed: HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise HttpCallError(f"Cognee remember transport failure: {exc.reason}") from exc
