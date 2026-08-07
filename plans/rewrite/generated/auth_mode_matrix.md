# Auth Mode Matrix

Route-method counts by inferred/verified auth mode to drive WS7 parity test coverage.

| Auth mode | Route rows | Primary route families |
|---|---:|---|
| `session-or-oauth2` | 274 | `api-v1`:268, `other`:6 |
| `session-or-anon-ui` | 55 | `web`:55 |
| `anon-allowed` | 23 | `registry-v1`:11, `web`:7, `other`:2, `secscan`:2 |
| `jwt-bearer` | 15 | `registry-v2`:15 |
| `legacy-registry-auth` | 15 | `registry-v1`:15 |
| `session-required` | 9 | `web`:3, `oauth2`:2, `realtime`:2, `oauth1`:1 |
| `oauth-flow-mixed` | 8 | `oauth2`:8 |
| `service-key-auth-mixed` | 4 | `keys`:4 |
| `jwt-bearer-or-anon` | 3 | `registry-v2`:3 |
| `webhook-shared-secret-or-signed-callback` | 3 | `webhooks`:3 |
| `anon-plus-psk-jwt-optional` | 2 | `other`:1, `secscan`:1 |
| `basic-or-external-auth-to-jwt` | 1 | `registry-v2`:1 |
| `storage-proxy-jwt` | 1 | `other`:1 |

## Required auth test categories
- Session + CSRF enforcement
- OAuth callback and grant flow behavior
- Registry JWT bearer scope behavior
- Anonymous access and restricted-user edge cases
- Webhook signature/secret validation
- Storage proxy JWT header validation (`/_storage_proxy_auth`)
