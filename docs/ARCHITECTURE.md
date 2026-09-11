# Architecture

```text
RocketRide operator / chat
          |
          v
RocketRide coding agent
   |          |          |
   v          v          v
Cognee     HydraDB     Hotdata
semantic   durable     live state
memory     graph       analytics
    \         |         /
     \        |        /
      v       v       v
       diagnosis / plan
              |
              v
        Tenki sandbox
      clone / edit / test
              |
              v
             Snyk
        security evidence
              |
              v
        Action Envelope
              |
              v
     external Gatekeeper V2
 ALLOW / TRANSFORM / HOLD / DENY
              |
       authorized effect only
              |
              v
       controlled GitHub effect
              |
              v
 Learning Event -> Cognee + HydraDB
 successful procedure -> Rote
```

Gatekeeper is the sole authority source. A Cognee recall, HydraDB relationship, Hotdata query, Tenki test pass, Snyk scan, RocketRide plan, or Rote replay may provide evidence or procedure but cannot authorize execution.

The Tenki sandbox does not receive unrestricted credentials capable of modifying the authoritative repository. It produces candidate changes and evidence. The final GitHub effect executes outside the sandbox only after an exact Gatekeeper decision is validated.

Operational telemetry is non-authoritative and must never be represented as a Gatekeeper receipt.
