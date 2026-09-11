from oasse_memory_muscle.contracts import ActionEnvelope, EvidenceRef


def make_action() -> ActionEnvelope:
    evidence = EvidenceRef(source="tests", ref="test://ok", sha256="0" * 64)
    return ActionEnvelope(
        tenant_id="oasse",
        principal_id="agent-1",
        actor_type="agent",
        session_id="run-1",
        delegation_id=None,
        source="rocketride",
        adapter="coding-agent",
        transaction_id="tx-1",
        parent_action_id=None,
        domain="software-change",
        action_type="open_pull_request",
        requested_effect="open PR with candidate patch",
        resource="demo_target/component_a.py",
        destination="main",
        repository="OakandSparrowSystemsEnterprises/OASSE-AWS-Memory-Muscle",
        base_sha="abcdef0",
        patch_sha256="1" * 64,
        evidence=(evidence,),
    )


def test_action_digest_is_stable():
    assert make_action().digest == make_action().digest


def test_action_digest_changes_with_effect():
    first = make_action()
    second = ActionEnvelope(**{**first.__dict__, "destination": "release"})
    assert first.digest != second.digest
