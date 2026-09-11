from __future__ import annotations

from dataclasses import dataclass

from .contracts import ActionEnvelope, AuthorityDecision, Verdict


class NonExecutableDecision(RuntimeError):
    pass


class AuthorityBindingError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutableAction:
    action: ActionEnvelope
    decision_id: str
    receipt_ref: str | None


def resolve_executable_action(action: ActionEnvelope, decision: AuthorityDecision) -> ExecutableAction:
    if decision.action_sha256 != action.digest:
        raise AuthorityBindingError("authority decision is not bound to this exact action")

    if decision.verdict in (Verdict.HOLD, Verdict.DENY):
        raise NonExecutableDecision(f"{decision.verdict.value} is not executable")

    if decision.verdict is Verdict.ALLOW:
        return ExecutableAction(action=action, decision_id=decision.decision_id, receipt_ref=decision.receipt_ref)

    if decision.verdict is Verdict.TRANSFORM:
        if decision.transformed_action is None:
            raise AuthorityBindingError("TRANSFORM missing transformed action")
        return ExecutableAction(action=decision.transformed_action, decision_id=decision.decision_id, receipt_ref=decision.receipt_ref)

    raise NonExecutableDecision("unknown authority verdict")
