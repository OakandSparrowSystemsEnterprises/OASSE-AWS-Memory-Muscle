# Sponsor contracts

RocketRide owns orchestration and the judge-facing agent flow. Proof: the real run is executed from the RocketRide pipeline.

Cognee owns semantic memory construction and recall. Dataset: `oasse-aws-hackathon`. Proof: a live remember/status/recall cycle is used by the coding-agent run.

HydraDB owns durable connected state across runs. Database: `oasse_aws_hackathon`. Proof: remediation relationships are persisted and queried on the second run.

Hotdata owns current run-scoped analytical state. Proof: current tests, changed files, scan results, or run metrics are loaded and queried live.

Rote owns reusable procedure. Proof: the first successful remediation is captured as a Play and the second run invokes the reusable method with fresh inputs.

Snyk owns security evidence. Proof: the candidate patch is scanned and the machine-readable result is attached to the Action Envelope evidence.

Tenki, when used, owns isolated execution. Proof: clone/edit/test occurs in the sandbox while the final repository write credential remains outside it.

Gatekeeper is preexisting OASSE technology, not a hackathon sponsor. It remains the sole execution-authority source.
