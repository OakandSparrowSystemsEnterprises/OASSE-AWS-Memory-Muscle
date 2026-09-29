# Continuity MVP

Continuity is a provider-neutral cognitive-lineage layer. It is deliberately not a shared-memory database.

The authoritative object is `ContinuityState`. A model receives a projection of that state, reasons over it, and proposes a `ContinuityTransition`. The model never owns or mutates the authoritative state directly. An authority port evaluates the exact transition digest. Only an `ALLOW` advances the lineage. `HOLD` and `DENY` leave the state byte-for-byte unchanged.

The core invariants are:

```text
one lineage != one model
remembered != trusted != authorized
```

History is append-only. A prior item may be superseded by a new item with provenance, but it is never silently deleted or rewritten.

## Current MVP

The deterministic replay hands one lineage from OpenAI to Anthropic to Google. The third handoff deliberately attempts to delete an unresolved item. The authority denies the transition and the authoritative state remains unchanged.

Run:

```bash
python -m continuity_mvp.demo
```

Expected decisions:

```text
OpenAI     ALLOW
Anthropic  ALLOW
Gemini     DENY
```

The denial is the feature. A model may contribute to the lineage, but it cannot become the authority that rewrites the lineage.

A live provider runner is also included:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export GEMINI_API_KEY=...
export CONTINUITY_PROVIDER_ORDER=openai,anthropic,google
python -m continuity_mvp.live_demo
```

Adapters are present for OpenAI Responses, Anthropic Messages, Gemini, xAI, Mistral, and DeepSeek. API credentials remain external. The deterministic replay remains the no-network conformance fixture so the security claim does not depend on any vendor being online.

## Research boundary

The MVP proves the mechanics of one append-only authoritative lineage and fail-closed handoffs. It does not yet prove a universal mathematical continuity invariant. The current `invariant_report` is intentionally conservative and structural: lineage identity, parent-state binding, active-item preservation, and provenance preservation.

The research program should extend that structural score with a falsifiable model of task-relevant sufficiency. The existing OASSE intertwiner work is a candidate formal tool because the target is preservation of structure across different representations, not equality of model outputs.

## Path to standalone product

This code lives on a separate branch of OASSE AWS Memory to Muscle only to reuse the existing memory, state, and governance substrate during validation. The package has no dependency on Cognee, HydraDB, Hotdata, Rote, or a particular model provider. After the transition contract and conformance suite stabilize, it can move into a standalone Continuity repository while Gatekeeper remains an external authority service.
