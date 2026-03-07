# Route Family Cutover Sequence

Recommended migration order by contract risk and dependency.

| Phase | Route family | Rows | Mutating rows | Notes |
|---|---|---:|---:|---|
| R1 | `registry-v2` | 19 | 9 | Start with auth/read paths, then push/upload/delete paths. |
| R2 | `registry-v1` | 26 | 12 | Keep full compatibility while v2 stabilizes; do not de-scope. |
| R3 | `oauth2` | 10 | 4 | Preserve callback route registration and redirect semantics. |
| R4 | `oauth1` | 1 | 0 | Preserve callback route registration and redirect semantics. |
| R5 | `api-v1` | 268 | 153 | Largest surface; prioritize read endpoints then mutations. |
| R6 | `webhooks` | 3 | 3 | Protect signature/secret validation semantics. |
| R7 | `keys` | 4 | 2 |  |
| R8 | `secscan` | 3 | 1 | Coordinate with security notification queue behavior. |
| R9 | `realtime` | 2 | 0 |  |
| R10 | `well-known` | 2 | 0 |  |
| R11 | `web` | 65 | 4 | Triage contract-critical endpoints vs pure UI render routes. |
| R12 | `other` | 10 | 3 | Includes app-level add_url_rule routes (`userfiles`, `_storage_proxy_auth`). |
