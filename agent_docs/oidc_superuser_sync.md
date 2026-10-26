# OIDC Superuser Group Sync

## Overview

OIDC Superuser Group Sync grants or revokes superuser (and global readonly superuser) privileges based on OIDC group membership. It is the OIDC equivalent of `LDAP_SUPERUSER_FILTER`.

Unlike LDAP, which queries the directory on each `is_superuser()` call, OIDC group claims are only available at login time. This feature syncs group membership into the in-memory `ConfigUserManager` shared arrays during the OIDC login flow, making the status visible to all gunicorn workers immediately.

## Configuration

Add `SUPERUSER_GROUP` and/or `GLOBAL_READONLY_SUPERUSER_GROUP` to your OIDC login service config block. `PREFERRED_GROUP_CLAIM_NAME` is required so that group claims are extracted from the OIDC token.

```yaml
# conf/stack/config.yaml
AUTHENTICATION_TYPE: OIDC

SUPER_USERS:
  - admin              # static superusers are always preserved

KEYCLOAK_LOGIN_CONFIG:
  CLIENT_ID: quay
  CLIENT_SECRET: <secret>
  OIDC_SERVER: https://keycloak.example.com/realms/master
  SERVICE_NAME: Keycloak
  LOGIN_SCOPES:
    - openid
    - profile
  PREFERRED_GROUP_CLAIM_NAME: groups         # required for group sync
  SUPERUSER_GROUP: quay-superusers           # OIDC group name
  GLOBAL_READONLY_SUPERUSER_GROUP: quay-readonly  # optional
```

Users in `SUPERUSER_GROUP` receive full superuser privileges at login. Users in `GLOBAL_READONLY_SUPERUSER_GROUP` receive read-only superuser access. Users removed from these groups lose the corresponding privileges on their next login.

Users listed in the static `SUPER_USERS` or `GLOBAL_READONLY_SUPER_USERS` config arrays are never deregistered, even if they are absent from the OIDC group.

## Key Implementation Files

| File | Purpose |
|------|---------|
| `data/users/externaloidc.py` | `sync_superuser_status()` — registers/deregisters via `app.usermanager` |
| `util/config/superusermanager.py` | `register_superuser()`, `deregister_superuser()`, and global readonly equivalents using `multiprocessing.Array` |
| `oauth/login_utils.py` | `sync_oidc_superusers()` — called at all 3 login paths in `_conduct_oauth_login()` |
| `data/users/__init__.py` | Reads `SUPERUSER_GROUP` / `GLOBAL_READONLY_SUPERUSER_GROUP` from OIDC service config and passes to `OIDCUsers()` |

## How It Works

```text
OIDC Login
  → exchange_code_for_login()          # extracts groups from token/userinfo
  → _conduct_oauth_login()
      → sync_oidc_groups()             # team sync (gated by FEATURE_TEAM_SYNCING)
      → sync_oidc_superusers()         # superuser sync (independent, always runs)
          → OIDCUsers.sync_superuser_status(user_groups, user_obj)
              → app.usermanager.register_superuser()   or deregister_superuser()
              → app.usermanager.register_global_readonly_superuser()  or deregister_...()

is_superuser(username) check (any request):
  → FederatedUserManager.is_superuser()
      → OIDCUsers.is_superuser() → returns None (no on-demand OIDC lookup)
      → falls back to ConfigUserManager.is_superuser() → checks shared array
```

Key behaviors:
- **Independent of team sync**: `sync_oidc_superusers()` is NOT gated by `FEATURE_TEAM_SYNCING`
- **Static user protection**: `deregister_superuser()` refuses to remove users from the initial `SUPER_USERS` config list
- **Cross-process visibility**: `ConfigUserManager` uses `multiprocessing.sharedctypes.Array`, which is allocated before gunicorn forks workers — all workers see updates immediately
- **Login-time only**: Status is synced at login. If a user is removed from the OIDC group, the change takes effect on their next login
- **Container-local**: Like all `ConfigUserManager` state, synced status lives in shared memory within a single container. In multi-replica deployments, a login handled by one pod updates only that pod's state. Other replicas will update when the same user logs in through them. This differs from `LDAP_SUPERUSER_FILTER`, which queries the directory on each `is_superuser()` call and therefore resolves consistently across all replicas without requiring a login on each one
- **Graceful no-op**: If `SUPERUSER_GROUP` is not configured, or if group claims are absent from the token, no sync occurs

## Keycloak Setup

To include group claims in the OIDC token:

1. In your Keycloak realm, go to **Clients** → your Quay client → **Client scopes** → **Dedicated scope**
2. Add a mapper: **Type** = "Group Membership", **Name** = "groups", **Token Claim Name** = "groups", **Full group path** = OFF
3. Ensure the groups claim appears in the userinfo endpoint response
4. Create the group (e.g. `quay-superusers`) and add users to it

The `PREFERRED_GROUP_CLAIM_NAME` in your Quay config must match the **Token Claim Name** from step 2.

## Testing

```bash
# OIDC superuser sync tests (sync_superuser_status, sync_user_groups integration)
TEST=true PYTHONPATH="." pytest test/test_external_oidc.py::OIDCSuperuserSyncTests -v

# ConfigUserManager register/deregister tests
TEST=true PYTHONPATH="." pytest util/config/test/test_superusermanager.py -v

# All OIDC tests
TEST=true PYTHONPATH="." pytest test/test_external_oidc.py -v
```
