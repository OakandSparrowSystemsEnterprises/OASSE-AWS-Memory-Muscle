from __future__ import annotations

import json

from .codec import decode_model_transition
from .contracts import ContinuityItem, ContinuityState, ItemKind, ProvenanceRef
from .kernel import ContinuityKernel, FailClosedAuthority, invariant_report


def initial_state() -> ContinuityState:
    return ContinuityState(
        lineage_id="continuity-rupert-demo-001",
        revision=0,
        parent_state_digest=None,
        current_model=None,
        items=(
            ContinuityItem("goal-1", ItemKind.GOAL, "Demonstrate one cognitive lineage surviving heterogeneous model handoffs."),
            ContinuityItem("fact-1", ItemKind.FACT, "There is one authoritative Continuity state; models are replaceable reasoning substrates.",
                           provenance=(ProvenanceRef("OASSE", "Continuity architecture decision"),)),
            ContinuityItem("open-1", ItemKind.OPEN_QUESTION, "Can a receiving model preserve unresolved state without silently converting uncertainty into fact?"),
            ContinuityItem("commit-1", ItemKind.COMMITMENT, "No model may delete or rewrite sealed lineage history.",
                           provenance=(ProvenanceRef("Gatekeeper", "append-only authority invariant"),)),
        ),
        authority_scope=("continuity.advance_lineage",),
    )


SCRIPTED = [
    ("openai:gpt-5.6-sol", json.dumps({
        "summary": "Preserve the open question and add the first handoff observation.",
        "append_items": [{"kind": "evidence", "text": "OpenAI received the authoritative state with the unresolved question still active.", "status": "active", "provenance": [{"source": "demo", "ref": "handoff-openai"}]}],
        "supersessions": [],
        "delete_item_ids": []
    })),
    ("anthropic:claude-opus-5", json.dumps({
        "summary": "Continue the same lineage and add a falsification requirement.",
        "append_items": [{"kind": "hypothesis", "text": "Continuity should fail its conformance gate if a provider drops an active unresolved item.", "status": "active", "provenance": [{"source": "demo", "ref": "handoff-anthropic"}]}],
        "supersessions": [],
        "delete_item_ids": []
    })),
    ("google:gemini-3.8-flash", json.dumps({
        "summary": "Attempt a prohibited cleanup to prove lineage authority remains external to the model.",
        "append_items": [{"kind": "evidence", "text": "Gemini can contribute new evidence without owning prior state.", "status": "active", "provenance": [{"source": "demo", "ref": "handoff-gemini"}]}],
        "supersessions": [],
        "delete_item_ids": ["open-1"]
    })),
]


def run() -> list[dict[str, object]]:
    kernel = ContinuityKernel(FailClosedAuthority())
    state = initial_state()
    rows: list[dict[str, object]] = []
    for model, raw in SCRIPTED:
        before = state
        transition = decode_model_transition(state, model, raw)
        state, decision = kernel.advance(state, transition)
        rows.append({
            "model": model,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "revision_before": before.revision,
            "revision_after": state.revision,
            "state_digest": state.digest,
            "invariant": invariant_report(before, state) if state is not before else {"continuity_score": 1.0, "state_unchanged": True},
        })
    return rows


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
