from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .boundary import ExecutableAction, resolve_executable_action
from .contracts import ActionEnvelope, AuthorityDecision
from .ports import AuthorityPort, EffectPort


@dataclass(frozen=True)
class GovernedEffectResult:
    executable: ExecutableAction
    effect_result: dict[str, Any]


def execute_governed_effect(action: ActionEnvelope, authority: AuthorityPort, effect: EffectPort) -> GovernedEffectResult:
    decision: AuthorityDecision = authority.evaluate(action)
    executable = resolve_executable_action(action, decision)
    effect_result = effect.execute(executable.action, decision)
    return GovernedEffectResult(executable=executable, effect_result=effect_result)
