# Operator runbook

At startup, run one readiness check per sponsor and cache/share the result. Do not allow multiple concurrent branches to hammer the same sponsor credentials.

Keep sponsor health separate from authority health. A support-plane failure must be reported as that sponsor's failure, not as a Gatekeeper failure.

Use the managed sponsor services already provisioned for the event. Do not self-host sponsor infrastructure unless the managed service is unavailable and the sponsor team explicitly recommends the fallback.

Do not place unrestricted GitHub write credentials inside Tenki. Do not place Gatekeeper journal state in sponsor databases. Do not reuse a prior Gatekeeper permit for a Rote replay.

For the live demo, prioritize one complete vertical over breadth.
