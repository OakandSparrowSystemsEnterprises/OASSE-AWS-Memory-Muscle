from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts import ActionEnvelope, AuthorityDecision, Verdict
from .http import HttpCallError, JsonHttpClient


class GatekeeperProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class GatekeeperHttpAdapter:
    base_url: str
    api_key: str
    evaluate_path: str
    timeout_seconds: float = 15.0

    def evaluate(self, action: ActionEnvelope) -> AuthorityDecision:
        client = JsonHttpClient(self.base_url, timeout_seconds=self.timeout_seconds)
        try:
            payload: Any = client.request_json(
                "POST",
                self.evaluate_path,
                payload={"action": action.canonical_dict(), "action_sha256": action.digest},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except HttpCallError:
            raise
        if not isinstance(payload, dict):
            raise GatekeeperProtocolError("Gatekeeper response must be a JSON object")

        raw_verdict = payload.get("verdict") or payload.get("decision")
        try:
            verdict = Verdict(str(raw_verdict).upper())
        except ValueError as exc:
            raise GatekeeperProtocolError(f"unsupported Gatekeeper verdict: {raw_verdict!r}") from exc

        action_sha = payload.get("action_sha256") or payload.get("actionSha256")
        if action_sha != action.digest:
            raise GatekeeperProtocolError("Gatekeeper decision is not bound to the exact action digest")

        if verdict is Verdict.TRANSFORM:
            raise GatekeeperProtocolError("TRANSFORM parsing is not enabled until the live Gatekeeper schema is confirmed")

        return AuthorityDecision(
            decision_id=str(payload.get("decision_id") or payload.get("decisionId") or ""),
            verdict=verdict,
            action_sha256=action_sha,
            policy_version=payload.get("policy_version") or payload.get("policyVersion"),
            receipt_ref=payload.get("receipt_ref") or payload.get("receiptRef"),
        )
