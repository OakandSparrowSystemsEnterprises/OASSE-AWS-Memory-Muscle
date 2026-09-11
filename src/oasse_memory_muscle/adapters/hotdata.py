"""Bounded Hotdata HTTP adapter. Context and analytics are not authority.

Reference: https://www.hotdata.dev/docs/api-reference
Only inline CSV loads and synchronous, database-scoped SQL are supported.
No database provisioning, deletion, automatic retry, or secret discovery occurs.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request


class HotdataError(RuntimeError):
    """Transport, provider, or response-contract failure; never permission."""


class HotdataPending(HotdataError):
    """The provider accepted background work; completion is not established."""


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HotdataError("Hotdata redirect refused; credentials were not forwarded")


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z_][a-z0-9_]{0,127}", value):
        raise ValueError("expected a lowercase identifier, not a path or SQL expression")
    return value


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\r" in value or "\n" in value:
        raise ValueError(f"{name} must be nonempty single-line text")
    return value


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""  # Provider CSV null/empty-field inference applies.
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) in (str, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("Hotdata rows require flat finite scalar values; flatten nested data first")


@dataclass(frozen=True)
class HotdataAdapter:
    api_key: str = field(repr=False)
    workspace_id: str
    database_id: str
    schema: str = "public"
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        _text(self.api_key, "api_key")
        _text(self.workspace_id, "workspace_id")
        _text(self.database_id, "database_id")
        if not re.fullmatch(r"work[a-z0-9]+", self.workspace_id):
            raise ValueError("workspace_id must be a Hotdata work... ID")
        if not re.fullmatch(r"dbid[a-z0-9]+", self.database_id):
            raise ValueError("database_id must be a Hotdata dbid... ID, not its display name")
        _identifier(self.schema)
        if type(self.timeout_seconds) not in (float, int) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        req = request.Request(
            "https://api.hotdata.dev" + path,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Workspace-Id": self.workspace_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with request.build_opener(_NoRedirect()).open(req, timeout=self.timeout_seconds) as response:
                if response.status == 202:
                    raise HotdataPending("Hotdata accepted background work; do not repeat the write or report completion")
                if response.status != 200:
                    raise HotdataError(f"Hotdata returned unexpected HTTP {response.status}")
                raw = response.read(4 * 1024 * 1024 + 1)
        except error.HTTPError as exc:
            # Provider error bodies can echo payloads or credentials. Keep them out of logs.
            raise HotdataError(f"Hotdata HTTP {exc.code}; no automatic retry") from None
        except (error.URLError, OSError):
            raise HotdataError("Hotdata transport failure or timeout; outcome may be unknown; no automatic retry") from None
        if len(raw) > 4 * 1024 * 1024:
            raise HotdataError("Hotdata response exceeds 4 MiB; narrow the query")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise HotdataError("Hotdata returned invalid JSON") from None
        if not isinstance(result, dict) or "error" in result:
            raise HotdataError("Hotdata response is not a successful JSON object")
        return result

    def table_for_run(self, run_id: str) -> str:
        _text(run_id, "run_id")
        return "oasse_run_" + hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]

    def qualified_table(self, run_id: str) -> str:
        return f"default.{self.schema}.{self.table_for_run(run_id)}"

    def load_rows(self, table: str, rows: list[dict[str, Any]], *, batch_id: str | None = None) -> dict[str, Any]:
        """Append inline CSV, preserving the provider acknowledgement.

        Supply a unique batch_id for distinct identical batches. Retrying the same
        rows/table/batch_id uses the same idempotency key. No automatic retry occurs.
        row_count in the acknowledgement is the TOTAL table count, not rows inserted.
        """
        _identifier(table)
        if not rows or not all(isinstance(row, dict) and row for row in rows):
            raise ValueError("rows must contain nonempty dictionaries")
        for row in rows:
            for key in row:
                _identifier(key)
        columns = sorted(rows[0])
        if any(set(row) != set(columns) for row in rows):
            raise ValueError("all rows in one load must have the same columns")
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row[name]) for name in columns])
        data = output.getvalue()
        if len(data.encode("utf-8")) > 2 * 1024 * 1024:
            raise ValueError("inline CSV exceeds 2 MiB; this adapter does not upload large files")
        if batch_id is not None:
            _text(batch_id, "batch_id")
        identity = [self.workspace_id, self.database_id, self.schema, table, batch_id, data]
        key = "oasse-" + hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()
        result = self._post(
            f"/v1/databases/{self.database_id}/schemas/{self.schema}/tables/{table}/loads",
            {"data": data, "mode": "append", "async": False, "idempotency_key": key},
        )
        count = result.get("row_count")
        if type(count) is not int or count < len(rows):
            raise HotdataError("Hotdata load did not acknowledge a valid total row count")
        if result.get("schema_name") != self.schema or result.get("table_name") != table:
            raise HotdataError("Hotdata load acknowledgement names a different schema or table")
        return result

    def load(self, run_id: str, rows: list[dict[str, Any]]) -> None:
        """LiveStatePort: stamp current run, append to its deterministic table."""
        table = self.table_for_run(run_id)
        if any(not isinstance(row, dict) or ("run_id" in row and row["run_id"] != run_id) for row in rows):
            raise ValueError("row run_id conflicts with the requested run")
        self.load_rows(table, [{**row, "run_id": run_id} for row in rows], batch_id=run_id)

    def query_raw(self, sql: str) -> dict[str, Any]:
        """Return the original provider response, including result/query IDs.

        SQL is the provider's read-only interface, not a local SQL security parser.
        Database selection is provided only in the body, never in two places.
        """
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("sql must be nonempty")
        return self._post("/v1/query", {
            "sql": sql, "database_id": self.database_id,
            "default_catalog": "default", "default_schema": self.schema, "async": False,
        })

    def query(self, sql: str) -> list[dict[str, Any]]:
        result = self.query_raw(sql)
        if result.get("truncated") is not False:
            raise HotdataError("Hotdata query is incomplete or truncation status is missing; use query_raw for result IDs")
        columns, rows = result.get("columns"), result.get("rows")
        if not isinstance(columns, list) or not all(isinstance(col, str) for col in columns) or len(set(columns)) != len(columns):
            raise HotdataError("Hotdata returned invalid or duplicate column names")
        if not isinstance(rows, list) or any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
            raise HotdataError("Hotdata returned malformed rows")
        count = result.get("preview_row_count", result.get("row_count"))
        if type(count) is not int or count != len(rows):
            raise HotdataError("Hotdata returned an inconsistent row count")
        return [dict(zip(columns, row)) for row in rows]
