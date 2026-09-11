# RocketRide pipeline

The submission `.pipe` will be exported here from RocketRide Cloud after the live pipeline is built.

The intended node roles are: operator/chat input -> coding agent -> Cognee memory -> HydraDB durable context -> Hotdata live state -> Tenki execution tool -> Snyk evidence -> governed-effect tool -> result/evidence output.

Do not hand-author a guessed `.pipe` schema. Build it in RocketRide Cloud using the event-supported nodes, run it successfully, then export the exact working `.pipe` into this directory for submission.
