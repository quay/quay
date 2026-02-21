# Rewrite Snapshot

Generated status snapshot across migration trackers.

- route rows: 413
- worker/process rows: 36
- runtime component rows: 8

## Route families
- `api-v1`: 268
- `keys`: 4
- `oauth1`: 1
- `oauth2`: 10
- `other`: 10
- `realtime`: 2
- `registry-v1`: 26
- `registry-v2`: 19
- `secscan`: 3
- `web`: 65
- `webhooks`: 3
- `well-known`: 2

## Worker verification
- `retired-approved`: 1
- `verified-source-anchored`: 35

## Route auth verification
- `source-anchored-needs-review`: 0
- `verified-source-anchored`: 413

## Runtime waves
- `W1`: 2
- `W2`: 4
- `W3`: 2

## Signoff batch coverage
- route rows with batch tags: 413/413
- worker rows with batch tags: 36/36
- distinct route batches: 4
- distinct worker batches: 7

## Decision status
- decisions pending: 0
- decisions approved: 5

## Notes
- `web=66` in `route_family_counts.md` (raw `@web.route` rows) reconciles to tracker `web=65` (method-level family rows) per `route_family_counts.md` reconciliation notes.
