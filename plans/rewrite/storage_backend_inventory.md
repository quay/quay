# Storage Backend Inventory and Migration Plan

Status: Draft (blocking)
Last updated: 2026-02-09

## 1. Purpose

Define migration strategy for all storage drivers and storage-routing behaviors used by Quay.

Primary source anchors:
- `storage/__init__.py`
- `storage/cloud.py`
- `storage/distributedstorage.py`
- `storage/downloadproxy.py`

## 2. Driver inventory (authoritative)

The Python registry currently registers 13 storage drivers:
1. `LocalStorage`
2. `S3Storage`
3. `GoogleCloudStorage`
4. `RadosGWStorage`
5. `SwiftStorage`
6. `CloudFrontedS3Storage`
7. `AzureStorage`
8. `RHOCSStorage`
9. `CloudFlareS3Storage`
10. `MultiCDNStorage`
11. `IBMCloudStorage`
12. `STSS3Storage`
13. `AkamaiS3Storage`

Additional compatibility-critical components:
- `DistributedStorage` (multi-location routing)
- `DownloadProxy` (`/_storage_proxy_auth` flow)

## 3. Migration strategy

1. Define a single Go storage interface for blob, manifest, and chunk operations.
2. Implement S3-compatible family first to maximize coverage quickly.
3. Preserve chunked-upload semantics and error normalization behavior.
4. Keep `DistributedStorage` routing semantics and placement invariants unchanged until explicit decision approved.
5. Validate signed-URL behavior for CDN-backed drivers via fixtures.
6. Repo mirror path uses Go-native `containers/image` (D-005 approved), with temporary compatibility fallback only during transition tests.

### CDN signing algorithm compatibility

- CloudFront (`CloudFrontedS3Storage`):
  - current behavior: RSA PKCS1v15 with SHA1 signing.
  - migration note: preserve exact provider compatibility; document FIPS-strict exception handling for SHA1 if needed.
- CloudFlare (`CloudFlareS3Storage`):
  - current behavior: RSA PKCS1v15 with SHA256 signing.
  - migration note: preserve signature payload and query-field contract.
- Akamai (`AkamaiS3Storage`):
  - current behavior: HMAC token generation via EdgeAuth (shared secret), not RSA URL signing.
  - migration note: preserve token name/window/query encoding behavior.

## 4. Delivery artifact

Track each driver in:
- `plans/rewrite/generated/storage_driver_migration_tracker.csv`

Required columns include:
- python driver
- Go implementation strategy (`native-sdk`, `s3-compatible-adapter`, `defer`)
- migration wave
- parity test ID
- rollout risk notes

## 5. Test requirements

- Driver contract tests run against Python and Go implementations.
- Mixed-runtime upload/download/read-after-write tests.
- Chunk resumability tests for interrupted uploads.
- Signed URL compatibility tests where applicable.

## 6. Exit criteria

- No cutover of storage-coupled capabilities without passing driver-specific contract tests.
- `DistributedStorage` and `DownloadProxy` parity explicitly verified.
- Every tracker row has owner and status set.
