from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ItemKind(str, Enum):
    GOAL = "goal"
    FACT = "fact"
    OPEN_QUESTION = "open_question"
    HYPOTHESIS = "hypothesis"
    COMMITMENT = "commitment"
    DECISION = "decision"
    EVIDENCE = "evidence"


class ItemStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class ProvenanceRef:
    source: str
    ref: str
    sha256: str | None = None

    def canonical_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuityItem:
    item_id: str
    kind: ItemKind
    text: str
    status: ItemStatus = ItemStatus.ACTIVE
    provenance: tuple[ProvenanceRef, ...] = ()
    supersedes: str | None = None
    created_by: str = "human"

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "kind": self.kind.value,
            "text": self.text,
            "status": self.status.value,
            "provenance": [p.canonical_dict() for p in self.provenance],
            "supersedes": self.supersedes,
            "created_by": self.created_by,
        }


@dataclass(frozen=True)
class ContinuityState:
    lineage_id: str
    revision: int
    parent_state_digest: str | None
    current_model: str | None
    items: tuple[ContinuityItem, ...] = ()
    authority_scope: tuple[str, ...] = ("continuity.advance_lineage",)
    handoff_history: tuple[str, ...] = ()

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "revision": self.revision,
            "parent_state_digest": self.parent_state_digest,
            "current_model": self.current_model,
            "items": [i.canonical_dict() for i in self.items],
            "authority_scope": list(self.authority_scope),
            "handoff_history": list(self.handoff_history),
        }

    @property
    def digest(self) -> str:
        return canonical_sha256(self.canonical_dict())

    def active_items(self) -> tuple[ContinuityItem, ...]:
        superseded = {i.supersedes for i in self.items if i.supersedes}
        return tuple(i for i in self.items if i.item_id not in superseded and i.status != ItemStatus.SUPERSEDED)


@dataclass(frozen=True)
class Supersession:
    old_item_id: str
    replacement: ContinuityItem

    def canonical_dict(self) -> dict[str, Any]:
        return {"old_item_id": self.old_item_id, "replacement": self.replacement.canonical_dict()}


@dataclass(frozen=True)
class ContinuityTransition:
    transition_id: str
    lineage_id: str
    base_state_digest: str
    proposed_by_model: str
    summary: str
    append_items: tuple[ContinuityItem, ...] = ()
    supersessions: tuple[Supersession, ...] = ()
    delete_item_ids: tuple[str, ...] = ()
    evidence: tuple[ProvenanceRef, ...] = ()

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "lineage_id": self.lineage_id,
            "base_state_digest": self.base_state_digest,
            "proposed_by_model": self.proposed_by_model,
            "summary": self.summary,
            "append_items": [i.canonical_dict() for i in self.append_items],
            "supersessions": [s.canonical_dict() for s in self.supersessions],
            "delete_item_ids": list(self.delete_item_ids),
            "evidence": [p.canonical_dict() for p in self.evidence],
        }

    @property
    def digest(self) -> str:
        return canonical_sha256(self.canonical_dict())


class Decision(str, Enum):
    ALLOW = "ALLOW"
    TRANSFORM = "TRANSFORM"
    HOLD = "HOLD"
    DENY = "DENY"


@dataclass(frozen=True)
class AuthorityDecision:
    decision: Decision
    transition_digest: str
    reason: str
    receipt_ref: str | None = None
