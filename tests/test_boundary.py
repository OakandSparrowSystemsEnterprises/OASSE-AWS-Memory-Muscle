import pytest

from oasse_memory_muscle.boundary import AuthorityBindingError, NonExecutableDecision, resolve_executable_action
from oasse_memory_muscle.contracts import AuthorityDecision, Verdict
from test_contracts import make_action


def test_allow_executes_exact_action():
    action = make_action()
    decision = AuthorityDecision(decision_id="d1", verdict=Verdict.ALLOW, action_sha256=action.digest)
    assert resolve_executable_action(action, decision).action == action


def test_hold_is_not_executable():
    action = make_action()
    decision = AuthorityDecision(decision_id="d2", verdict=Verdict.HOLD, action_sha256=action.digest)
    with pytest.raises(NonExecutableDecision):
        resolve_executable_action(action, decision)


def test_deny_is_not_executable():
    action = make_action()
    decision = AuthorityDecision(decision_id="d3", verdict=Verdict.DENY, action_sha256=action.digest)
    with pytest.raises(NonExecutableDecision):
        resolve_executable_action(action, decision)


def test_mismatched_digest_fails_closed():
    action = make_action()
    decision = AuthorityDecision(decision_id="d4", verdict=Verdict.ALLOW, action_sha256="f" * 64)
    with pytest.raises(AuthorityBindingError):
        resolve_executable_action(action, decision)
