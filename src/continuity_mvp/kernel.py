from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .contracts import AuthorityDecision, ContinuityState, ContinuityTransition, Decision, ItemStatus


class ContinuityError(RuntimeError):
    pass


class AuthorityPort(Protocol):
    def authorize(self, state: ContinuityState, transition: ContinuityTransition) -> AuthorityDecision: ...


class FailClosedAuthority:
    """Deterministic MVP authority. Production can replace this port with Gatekeeper V2."""

    def authorize(self, state: ContinuityState, transition: ContinuityTransition) -> AuthorityDecision:
        if transition.base_state_digest != state.digest:
            return AuthorityDecision(Decision.HOLD, transition.digest, "base-state digest mismatch")
        if transition.lineage_id != state.lineage_id:
            return AuthorityDecision(Decision.DENY, transition.digest, "lineage substitution rejected")
        if transition.delete_item_ids:
            return AuthorityDecision(Decision.DENY, transition.digest, "sealed continuity state is append-only")

        existing = {i.item_id: i for i in state.items}
        proposed_ids = [i.item_id for i in transition.append_items]
        proposed_ids += [s.replacement.item_id for s in transition.supersessions]
        if len(proposed_ids) != len(set(proposed_ids)) or any(i in existing for i in proposed_ids):
            return AuthorityDecision(Decision.DENY, transition.digest, "item identity collision")

        for supersession in transition.supersessions:
            old = existing.get(supersession.old_item_id)
            if old is None:
                return AuthorityDecision(Decision.HOLD, transition.digest, "supersession target is not authoritative")
            if supersession.replacement.supersedes != old.item_id:
                return AuthorityDecision(Decision.DENY, transition.digest, "replacement is not bound to superseded item")
            if old.kind.value in {"fact", "commitment", "decision"} and not supersession.replacement.provenance:
                return AuthorityDecision(Decision.HOLD, transition.digest, "material supersession requires provenance")

        return AuthorityDecision(Decision.ALLOW, transition.digest, "transition satisfies MVP continuity invariants")


class ContinuityKernel:
    def __init__(self, authority: AuthorityPort):
        self.authority = authority

    def advance(self, state: ContinuityState, transition: ContinuityTransition) -> tuple[ContinuityState, AuthorityDecision]:
        if transition.base_state_digest != state.digest:
            raise ContinuityError("transition was not built from the supplied authoritative state")

        decision = self.authority.authorize(state, transition)
        if decision.transition_digest != transition.digest:
            raise ContinuityError("authority decision is not bound to exact transition digest")
        if decision.decision is not Decision.ALLOW:
            return state, decision

        items = list(state.items)
        existing = {i.item_id: i for i in items}

        for supersession in transition.supersessions:
            old = existing[supersession.old_item_id]
            if old.status != ItemStatus.SUPERSEDED:
                idx = next(n for n, item in enumerate(items) if item.item_id == old.item_id)
                items[idx] = replace(old, status=ItemStatus.SUPERSEDED)
            items.append(supersession.replacement)

        items.extend(transition.append_items)
        next_state = ContinuityState(
            lineage_id=state.lineage_id,
            revision=state.revision + 1,
            parent_state_digest=state.digest,
            current_model=transition.proposed_by_model,
            items=tuple(items),
            authority_scope=state.authority_scope,
            handoff_history=state.handoff_history + (transition.proposed_by_model,),
        )
        return next_state, decision


def invariant_report(before: ContinuityState, after: ContinuityState) -> dict[str, object]:
    before_active = {i.item_id: i for i in before.active_items()}
    after_items = {i.item_id: i for i in after.items}
    preserved_ids = [i for i in before_active if i in after_items]
    provenance_preserved = all(before_active[i].provenance == after_items[i].provenance for i in preserved_ids)
    same_lineage = before.lineage_id == after.lineage_id
    parent_bound = after.parent_state_digest == before.digest
    protected_total = max(1, len(before_active))
    structural_ratio = len(preserved_ids) / protected_total
    score = structural_ratio
    if not provenance_preserved:
        score *= 0.5
    if not same_lineage:
        score = 0.0
    if not parent_bound:
        score *= 0.5
    return {
        "same_lineage": same_lineage,
        "parent_bound": parent_bound,
        "active_items_preserved": len(preserved_ids),
        "active_items_total": len(before_active),
        "provenance_preserved": provenance_preserved,
        "structural_ratio": round(structural_ratio, 6),
        "continuity_score": round(score, 6),
    }
