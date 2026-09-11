# Demo target

This is a deliberately small two-stage coding target for the live hackathon demonstration. The main project test configuration excludes this directory so the infrastructure skeleton can remain green while the demo target starts with known failures.

Run one targets `component_a.py`. Run two targets `component_b.py`. Both express the same retry-backoff bug class so the second run can demonstrate reusable memory/procedure rather than a memorized patch.

Use the component-specific tests as the remediation acceptance criteria.
