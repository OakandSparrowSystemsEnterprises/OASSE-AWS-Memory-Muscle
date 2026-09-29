from __future__ import annotations

import json
import re
import uuid

from .contracts import ContinuityItem, ContinuityState, ContinuityTransition, ItemKind, ItemStatus, ProvenanceRef, Supersession


def _parse_json_object(text: str) -> dict:
    clean = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", clean, flags=re.S | re.I)
    if fenced:
        clean = fenced.group(1)
    value = json.loads(clean)
    if not isinstance(value, dict):
        raise ValueError("model transition must be a JSON object")
    return value


def _provenance(rows) -> tuple[ProvenanceRef, ...]:
    out = []
    for row in rows or []:
        if isinstance(row, str):
            out.append(ProvenanceRef(source="model", ref=row))
        elif isinstance(row, dict):
            out.append(ProvenanceRef(source=str(row.get("source", "model")), ref=str(row.get("ref", "")), sha256=row.get("sha256")))
    return tuple(out)


def _item(row: dict, *, model: str, supersedes: str | None = None) -> ContinuityItem:
    return ContinuityItem(
        item_id=str(row.get("item_id") or f"ci-{uuid.uuid4().hex[:12]}"),
        kind=ItemKind(str(row["kind"])),
        text=str(row["text"]).strip(),
        status=ItemStatus(str(row.get("status", "active"))),
        provenance=_provenance(row.get("provenance")),
        supersedes=supersedes or row.get("supersedes"),
        created_by=model,
    )


def decode_model_transition(state: ContinuityState, model: str, text: str) -> ContinuityTransition:
    data = _parse_json_object(text)
    supersessions = []
    for row in data.get("supersessions", []):
        old_id = str(row["old_item_id"])
        replacement = _item(row["replacement"], model=model, supersedes=old_id)
        supersessions.append(Supersession(old_id, replacement))

    return ContinuityTransition(
        transition_id=str(data.get("transition_id") or f"ct-{uuid.uuid4().hex[:12]}"),
        lineage_id=state.lineage_id,
        base_state_digest=state.digest,
        proposed_by_model=model,
        summary=str(data.get("summary", "")).strip(),
        append_items=tuple(_item(row, model=model) for row in data.get("append_items", [])),
        supersessions=tuple(supersessions),
        delete_item_ids=tuple(str(x) for x in data.get("delete_item_ids", [])),
        evidence=(),
    )
