from __future__ import annotations

import json
import os

from .codec import decode_model_transition
from .demo import initial_state
from .kernel import ContinuityKernel, FailClosedAuthority, invariant_report
from .providers import AnthropicAdapter, GeminiAdapter, OpenAICompatibleAdapter, OpenAIResponsesAdapter


def adapters_from_env():
    return {
        "openai": OpenAIResponsesAdapter.from_env(),
        "anthropic": AnthropicAdapter.from_env(),
        "google": GeminiAdapter.from_env(),
        "xai": OpenAICompatibleAdapter.xai_from_env(),
        "mistral": OpenAICompatibleAdapter.mistral_from_env(),
        "deepseek": OpenAICompatibleAdapter.deepseek_from_env(),
    }


def run_live(instruction: str = "Continue the active Continuity research task. Add only information you can support and preserve unresolved questions.") -> list[dict[str, object]]:
    registry = adapters_from_env()
    order = [x.strip() for x in os.getenv("CONTINUITY_PROVIDER_ORDER", "openai,anthropic,google").split(",") if x.strip()]
    unknown = [x for x in order if x not in registry]
    if unknown:
        raise ValueError(f"unknown providers: {unknown}")

    kernel = ContinuityKernel(FailClosedAuthority())
    state = initial_state()
    rows: list[dict[str, object]] = []
    for name in order:
        adapter = registry[name]
        before = state
        result = adapter.complete(state, instruction)
        transition = decode_model_transition(state, f"{result.provider}:{result.model}", result.text)
        state, decision = kernel.advance(state, transition)
        rows.append({
            "provider": result.provider,
            "model": result.model,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "revision_before": before.revision,
            "revision_after": state.revision,
            "state_digest": state.digest,
            "continuity": invariant_report(before, state) if state is not before else {"state_unchanged": True, "continuity_score": 1.0},
        })
        if decision.decision.value in {"HOLD", "DENY"}:
            break
    return rows


if __name__ == "__main__":
    print(json.dumps(run_live(), indent=2))
