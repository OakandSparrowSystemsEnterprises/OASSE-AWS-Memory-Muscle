from continuity_mvp.codec import decode_model_transition
from continuity_mvp.contracts import ContinuityItem, ContinuityState, ItemKind, ProvenanceRef
from continuity_mvp.demo import run
from continuity_mvp.kernel import ContinuityKernel, FailClosedAuthority, invariant_report


def state():
    return ContinuityState(
        lineage_id="test-lineage",
        revision=0,
        parent_state_digest=None,
        current_model=None,
        items=(
            ContinuityItem("goal", ItemKind.GOAL, "Preserve one lineage."),
            ContinuityItem("fact", ItemKind.FACT, "History is append-only", provenance=(ProvenanceRef("test", "fact"),)),
            ContinuityItem("open", ItemKind.OPEN_QUESTION, "Still unresolved?"),
        ),
    )


def test_allowed_handoff_preserves_structure():
    before = state()
    raw = """{
      "summary":"continue",
      "append_items":[{"kind":"evidence","text":"new observation","status":"active","provenance":[{"source":"test","ref":"obs"}]}],
      "supersessions":[],
      "delete_item_ids":[]
    }"""
    transition = decode_model_transition(before, "provider:model", raw)
    after, decision = ContinuityKernel(FailClosedAuthority()).advance(before, transition)
    assert decision.decision.value == "ALLOW"
    assert after.revision == 1
    assert after.parent_state_digest == before.digest
    assert invariant_report(before, after)["continuity_score"] == 1.0
    assert any(i.item_id == "open" for i in after.active_items())


def test_model_cannot_delete_unresolved_state():
    before = state()
    raw = """{
      "summary":"cleanup",
      "append_items":[],
      "supersessions":[],
      "delete_item_ids":["open"]
    }"""
    transition = decode_model_transition(before, "provider:model", raw)
    after, decision = ContinuityKernel(FailClosedAuthority()).advance(before, transition)
    assert decision.decision.value == "DENY"
    assert after.digest == before.digest


def test_material_supersession_requires_provenance():
    before = state()
    raw = """{
      "summary":"rewrite fact",
      "append_items":[],
      "supersessions":[{
        "old_item_id":"fact",
        "replacement":{"kind":"fact","text":"History may be rewritten","status":"active","provenance":[]}
      }],
      "delete_item_ids":[]
    }"""
    transition = decode_model_transition(before, "provider:model", raw)
    after, decision = ContinuityKernel(FailClosedAuthority()).advance(before, transition)
    assert decision.decision.value == "HOLD"
    assert after.digest == before.digest


def test_rupert_replay_has_two_advances_then_fail_closed():
    rows = run()
    assert [r["decision"] for r in rows] == ["ALLOW", "ALLOW", "DENY"]
    assert rows[-1]["revision_before"] == rows[-1]["revision_after"]
