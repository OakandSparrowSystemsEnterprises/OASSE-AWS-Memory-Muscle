# OASSE AWS Memory to Muscle

Oak & Sparrow Systems Enterprise LLC entry for the September 11, 2026 AWS Data & AI Hackathon.

This project is an AI coding agent that compounds knowledge and successful procedure across runs without allowing memory, orchestration, compute, or prior success to become execution authority.

RocketRide is the orchestration control plane. Cognee constructs semantic memory. HydraDB stores durable connected state. Hotdata provides live run-scoped repository state and analytics. Tenki is the isolated execution workbench. Snyk produces security evidence. Rote captures successful procedure as reusable muscle memory. Gatekeeper V2 remains a preexisting external OASSE pre-execution authority service.

The invariant is: memory may recommend a known procedure, but every consequential effect requires a fresh Gatekeeper authorization bound to the exact action.

## Event provenance

This repository was created after the organizers announced the hackathon build window open. Pre-event work consisted of planning, account setup, sponsor warm-ups, architectural research, and a non-submission scratch skeleton in a separate repository. This repository contains the official event-time implementation history.

## Build target

The first vertical is: failing code -> current-state query -> memory recall -> isolated remediation -> tests -> Snyk evidence -> exact Action Envelope -> Gatekeeper decision -> controlled GitHub effect -> Learning Event -> Rote capture.

The second run repeats the failure class on a different component and must reuse learned procedure while still obtaining fresh authorization.

## Local contract checks

```bash
python -m pip install -e ".[dev]"
pytest
python scripts/check_skeleton.py
```

## IP boundary

Code distributed in this repository is licensed under the MIT License. The license does not extend to Gatekeeper production/runtime source, proprietary policy corpora, private OASSE infrastructure, private enterprise integrations, credentials, patents or patent applications, trade secrets, or other OASSE technology not distributed here. Gatekeeper is consumed only through its external API boundary.
