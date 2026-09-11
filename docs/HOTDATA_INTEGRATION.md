# Hotdata integration

The event uses the existing `hackathon-test` database, ID `dbidfb8ewsy6zs3ze98j895xggqbe8`, in workspace `work51ixe3fjw5xpdxuv7xblatwghh`, catalog `default`, schema `public`. These are resource identifiers, not credentials. Pass the existing local token to `HotdataAdapter`; do not commit it. This adapter introduces no SDK dependency and does not recreate the database.

## Confirmed external probe

The operator reported a successful live load and SQL retrieval on September 11, 2026, both HTTP 200, with one synthetic record. The table was `default.public.oasse_retry_backoff_cap_60f9496fa9114804b329ad552e442d38`, and its record_id was `60f9496fa9114804b329ad552e442d38`. This is user-reported live connection evidence, not proof that this newly committed adapter was itself run against the service. The full local result file was not copied into the public repository.

## Adapter interface

```python
import os
from oasse_memory_muscle.adapters.hotdata import HotdataAdapter

hotdata = HotdataAdapter(
    api_key=os.environ["HOTDATA_API_KEY"],
    workspace_id="work51ixe3fjw5xpdxuv7xblatwghh",
    database_id="dbidfb8ewsy6zs3ze98j895xggqbe8",
    schema="public",
)

# Read existing proof once without another load.
rows = hotdata.query(
    "SELECT * FROM default.public.oasse_retry_backoff_cap_60f9496fa9114804b329ad552e442d38 "
    "WHERE record_id = '60f9496fa9114804b329ad552e442d38' LIMIT 1"
)
```

`load(run_id, rows)` implements LiveStatePort and stamps each row with run_id. `qualified_table(run_id)` gives the SQL table for those rows. Use a new run_id for each real execution and a fixed flat column shape. Run-specific tables are logical separation inside this existing database, not per-agent database or security isolation. This Main Track integration does not claim the separate Parallel Agents database lifecycle requirement.

`load_rows(table, rows, batch_id=...)` supports a caller-selected table and returns the original acknowledgement. It uses append rather than replace, deterministic idempotency keys, and inline CSV within the documented 2 MiB bound. The acknowledged row_count is total table rows, not rows inserted. None is encoded as an empty CSV field, so exact null-versus-empty-string preservation is not promised. Do not change a table's column set between loads.

`query_raw(sql)` returns provider metadata alongside results. `query(sql)` converts complete row arrays and column names to dictionaries, refusing truncated or malformed responses. A returned HTTP 202 is pending, not success. Errors and uncertain outcomes are not automatically retried. The adapter refuses redirects and does not include credentials or provider error bodies in its exception messages.

## Demo evidence

Connectivity records are synthetic fixtures. They must not be counted as successful repairs or learned-from-execution memory. The setup fixture already names the proposed retry-backoff remedy; any demo using it must disclose it as seeded context, not newly discovered learning. Record actual test results, code hashes and run IDs separately. No Hotdata result grants Gatekeeper authorization.

## Sources

Endpoint, authentication and response contracts were checked against official Hotdata documentation on September 11, 2026:

https://www.hotdata.dev/docs/api-reference

https://www.hotdata.dev/docs/api-reference/databases

https://www.hotdata.dev/docs/api-reference/query

The accompanying 38 tests use offline transport responses. They test the adapter, not live credentials or the complete sponsor workflow.
