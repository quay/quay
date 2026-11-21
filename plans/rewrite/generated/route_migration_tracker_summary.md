# Route Migration Tracker Summary

- total rows: 413
- by route_family:
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
- by auth_mode:
  - `anon-allowed`: 23
  - `anon-plus-psk-jwt-optional`: 2
  - `basic-or-external-auth-to-jwt`: 1
  - `jwt-bearer`: 15
  - `jwt-bearer-or-anon`: 3
  - `legacy-registry-auth`: 15
  - `oauth-flow-mixed`: 8
  - `service-key-auth-mixed`: 4
  - `session-or-anon-ui`: 55
  - `session-or-oauth2`: 274
  - `session-required`: 9
  - `storage-proxy-jwt`: 1
  - `webhook-shared-secret-or-signed-callback`: 3

## Notes
- `auth_mode` values are inference-backed; routes with prior `unknown` are manually verified and annotated in `notes`.
- Includes supplemental non-blueprint routes from `app.add_url_rule` (see `non_blueprint_route_inventory.md`).
- `cutover_switch_id` values are proposed IDs to seed the capability switch namespace.
