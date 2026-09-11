from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    TRANSFORM = "TRANSFORM"
    HOLD = "HOLD"
    DENY = "DENY"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    ref: str
    sha256: str

    def __post_init__(self) -> None:
        if len(self.sha256) != 64:
            raise ValueError("evidence sha256 must be a 64-character hex digest")
        int(self.sha256, 16)


@dataclass(frozen=True)
class ActionEnvelope:
    tenant_id: str
    principal_id: str
    actor_type: str
    session_id: str
    delegation_id: str | None
    source: str
    adapter: str
    transaction_id: str
    parent_action_id: str | None
    domain: str
    action_type: str
    requested_effect: str
    resource: str
    destination: str
    repository: str
    base_sha: str
    patch_sha256: str
    evidence: tuple[EvidenceRef, ...] = ()

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "principal_id": self.principal_id,
            "actor_type": self.actor_type,
            "session_id": self.session_id,
            "delegation_id": self.delegation_id,
            "source": self.source,
            "adapter": self.adapter,
            "transaction_id": self.transaction_id,
            "parent_action_id": self.parent_action_id,
            "domain": self.domain,
            "action_type": self.action_type,
            "requested_effect": self.requested_effect,
            "resource": self.resource,
            "destination": self.destination,
            "repository": self.repository,
            "base_sha": self.base_sha,
            "patch_sha256": self.patch_sha256,
            "evidence": [asdict(item) for item in self.evidence],
        }

    @property
    def digest(self) -> str:
        return canonical_sha256(self.canonical_dict())


@dataclass(frozen=True)
class AuthorityDecision:
    decision_id: str
    verdict: Verdict
    action_sha256: str
    policy_version: str | None = None
    transformed_action: ActionEnvelope | None = None
    receipt_ref: str | None = None

    def __post_init__(self) -> None:
        if len(self.action_sha256) != 64:
            raise ValueError("action_sha256 must be a 64-character hex digest")
        int(self.action_sha256, 16)
        if self.verdict is Verdict.TRANSFORM and self.transformed_action is None:
            raise ValueError("TRANSFORM requires transformed_action")
        if self.verdict is not Verdict.TRANSFORM and self.transformed_action is not None:
            raise ValueError("transformed_action is valid only for TRANSFORM")


@dataclass(frozen=True)
class LearningEvent:
    event_id: str
    run_id: str
    repository: str
    base_sha: str
    failure_signature: str
    diagnosis: str
    remediation_summary: str
    patch_sha256: str
    test_evidence: tuple[EvidenceRef, ...]
    security_evidence: tuple[EvidenceRef, ...]
    authority_decision_id: str
    authority_receipt_ref: str | None
    success: bool

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "repository": self.repository,
            "base_sha": self.base_sha,
            "failure_signature": self.failure_signature,
            "diagnosis": self.diagnosis,
            "remediation_summary": self.remediation_summary,
            "patch_sha256": self.patch_sha256,
            "test_evidence": [asdict(item) for item in self.test_evidence],
            "security_evidence": [asdict(item) for item in self.security_evidence],
            "authority_decision_id": self.authority_decision_id,
            "authority_receipt_ref": self.authority_receipt_ref,
            "success": self.success,
        }

    @property
    def digest(self) -> str:
        return canonical_sha256(self.canonical_dict())
