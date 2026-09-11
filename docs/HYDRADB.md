# HydraDB API v2 integration

The operator reported a live HTTP 202 ingestion followed by HTTP 200 retrieval on September 11, 2026. The working database is `oasse_aws_hackathon`; the API-written record is in collection `default`. This is separate from the earlier dashboard upload in collection `oasse_aws_hackathon`.

The verified connection-test record ID is `learning-retry-backoff-cap-bd90d10eaff044ebaf1a9feb49cbe585`. It contains a synthetic retry-backoff lesson, not evidence of a completed code repair or a Gatekeeper decision.

## Implementation

`HydraDBAdapter` uses Python standard-library HTTP. No new package, database, plugin, or browser setup is required. Import it from `oasse_memory_muscle.adapters.hydradb`.

`ingest_memory(text, record_id=...)` posts multipart data to `/context/ingest`. `query(text, source_ids=(... ,))` posts JSON to `/query`. Both send `API-Version: 2`, bearer authentication, and the configured database and collection. Writes set `upsert=false` and are never automatically retried. Use a unique event ID for a new event.

`query` preserves the response body, HTTP status and request ID. `related_context` exposes the documented `data.chunks` array without inventing an answer. Unknown response shapes raise an error instead of becoming empty successful recall.

`store_learning_event` serializes the existing canonical LearningEvent as memory text and returns a JSON acknowledgement. HTTP 202 means queued, not indexed. The acknowledgement is not an authoritative receipt. A later retrieval must demonstrate availability before a downstream agent relies on the memory.

## Configuration

`from_env()` accepts the existing `HYDRADB_API_KEY` name or `HYDRA_DB_API_KEY`. It does not scan the computer or load files automatically. The caller may reuse its existing private environment loader.

The default database is `oasse_aws_hackathon`; override with `HYDRADB_DATABASE` or the existing `HYDRADB_TENANT_ID`. The default collection is `default`; override with `HYDRADB_COLLECTION`. `HYDRADB_BASE_URL` defaults to `https://api.hydradb.com`. No credential values belong in this repository.

## Evidence boundary

The initial live round-trip is operator-reported. The adapter's transport tests are offline fixtures, not live API evidence. A live run of this new adapter and graph-relationship retrieval are not yet claimed. Existing Cognee code and Gatekeeper code are unchanged.

## Protocol references

HydraDB's official Python SDK reference documents the v2 wire contract: https://pypi.org/project/hydradb-sdk/ . The official TypeScript SDK reference also documents the v2 endpoint paths and snake_case wire fields: https://www.npmjs.com/package/@hydradb/sdk . Some older pages at https://docs.hydradb.com/api-reference still describe legacy tenant/recall routes. This adapter uses the v2 routes confirmed by the live test, not those legacy routes.
