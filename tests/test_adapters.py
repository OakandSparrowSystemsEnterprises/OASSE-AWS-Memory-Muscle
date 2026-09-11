from __future__ import annotations

import pytest

from oasse_memory_muscle.adapters.cognee import CogneeAdapter
from oasse_memory_muscle.adapters.gatekeeper import GatekeeperHttpAdapter, GatekeeperProtocolError
from oasse_memory_muscle.adapters.http import JsonHttpClient
from oasse_memory_muscle.contracts import ActionEnvelope


def sample_action() -> ActionEnvelope:
    return ActionEnvelope(
        tenant_id="oasse",
        principal_id="hackathon-operator",
        actor_type="agent",
        session_id="run-1",
        delegation_id=None,
        source="rocketride",
        adapter="github-effect",
        transaction_id="tx-1",
        parent_action_id=None,
        domain="software",
        action_type="open_pull_request",
        requested_effect="create PR with candidate patch",
        resource="demo_target/component_a.py",
        destination="main",
        repository="OakandSparrowSystemsEnterprises/OASSE-AWS-Memory-Muscle",
        base_sha="abc123",
        patch_sha256="0" * 64,
    )


def test_cognee_recall_normalizes_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(self, method, path, *, payload=None, headers=None):
        assert method == "POST"
        assert path == "/api/v1/recall"
        assert headers == {"X-Api-Key": "key"}
        assert payload["datasets"] == ["oasse-aws-hackathon"]
        return [{"answer": "OASSE Cognee connection test"}]

    monkeypatch.setattr(JsonHttpClient, "request_json", fake_request)
    adapter = CogneeAdapter("https://tenant.example", "key", "oasse-aws-hackathon")
    assert adapter.recall("connection test") == ["OASSE Cognee connection test"]


def test_gatekeeper_rejects_digest_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    action = sample_action()

    def fake_request(self, method, path, *, payload=None, headers=None):
        return {
            "decision_id": "d1",
            "verdict": "ALLOW",
            "action_sha256": "f" * 64,
            "receipt_ref": "receipt-1",
        }

    monkeypatch.setattr(JsonHttpClient, "request_json", fake_request)
    adapter = GatekeeperHttpAdapter("https://gatekeeper.example", "key", "/evaluate")
    with pytest.raises(GatekeeperProtocolError, match="exact action digest"):
        adapter.evaluate(action)


def test_gatekeeper_accepts_exact_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    action = sample_action()

    def fake_request(self, method, path, *, payload=None, headers=None):
        return {
            "decision_id": "d1",
            "verdict": "ALLOW",
            "action_sha256": action.digest,
            "receipt_ref": "receipt-1",
        }

    monkeypatch.setattr(JsonHttpClient, "request_json", fake_request)
    decision = GatekeeperHttpAdapter("https://gatekeeper.example", "key", "/evaluate").evaluate(action)
    assert decision.action_sha256 == action.digest
    assert decision.receipt_ref == "receipt-1"
