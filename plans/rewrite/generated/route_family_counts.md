# Route Family Counts

- Flask-RESTful `@resource` route rows: 176
- Blueprint `bitbuckettrigger` route rows: 1
- Blueprint `federation_bp` route rows: 1
- Blueprint `githubtrigger` route rows: 1
- Blueprint `gitlabtrigger` route rows: 1
- Blueprint `key_server` route rows: 4
- Blueprint `realtime` route rows: 2
- Blueprint `secscan` route rows: 3
- Blueprint `v1_bp` route rows: 24
- Blueprint `v2_bp` route rows: 19
- Blueprint `web` route rows: 66
- Blueprint `webhooks` route rows: 3
- Blueprint `wellknown` route rows: 2
- App-level `add_url_rule` route rows (outside blueprints/resources): 3

## Reconciliation Notes

`web=66` in this file and `web=65` in `route_migration_tracker.csv` are both correct because they measure different things:

1. This file's `Blueprint web route rows: 66` counts raw `@web.route(...)` decorator rows.
2. The tracker's `route_family=web` count (65) is method-level and family-classified.

Reconciliation math (from `endpoints/web.py`):
- Raw `@web.route` decorator rows: 66.
- Reclassified out of `web` family by path prefix:
  - `/api/v1/user/initialize` -> `api-v1` (1 row)
  - `/v1` and `/v1/` -> `registry-v1` (2 rows)
- Multi-method expansion in tracker:
  - `/config` has `GET, OPTIONS` (+1 additional method row)
  - `/csrf_token` has `GET, OPTIONS` (+1 additional method row)

Result: `66 - 3 + 2 = 65` method-level `web` rows in tracker/snapshot.
