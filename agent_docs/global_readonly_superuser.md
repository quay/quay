# Global Read Only Superuser

## Overview

Global Read Only Superusers have read access to all repositories and resources across the registry, but cannot perform any write operations. This is useful for auditing and monitoring.

## Configuration

```yaml
# conf/stack/config.yaml
SUPER_USERS:
  - admin
GLOBAL_READONLY_SUPER_USERS:
  - quayadmin
  - readonly
```

## Key Implementation Files

| File | Purpose |
|------|---------|
| `util/config/superusermanager.py` | `is_global_readonly_superuser()` check |
| `auth/permissions.py` | Permission classes with global readonly support |
| `endpoints/api/__init__.py` | `allow_if_global_readonly_superuser()` helper |
| `endpoints/v2/__init__.py` | V2 permission decorators |

## API v1 Support

Add support to endpoints via decorator parameter:

```python
@require_repo_read(allow_for_global_readonly_superuser=True)
def get_repository(namespace, repository):
    # Global readonly superusers can access this
```

## API v2 Support

V2 endpoints require explicit support:

```python
@require_repo_read(allow_for_superuser=True, allow_for_global_readonly_superuser=True)
def list_tags(namespace_name, repo_name):
    # V2 endpoint accessible to global readonly superusers
```

## Write Operation Blocking

Global readonly superusers are blocked from writes at multiple levels:

1. **Permission Classes** (`auth/permissions.py`): Each write permission class checks and blocks global readonly superusers

2. **Superuser Function** (`endpoints/api/__init__.py`): `allow_if_superuser()` excludes global readonly superusers from write privileges

3. **Endpoint Level**: Individual endpoints may have additional checks

## Robot Account Access

GROSU can access organization robot account endpoints for audit purposes, but
robot tokens are credentials that enable authentication as the robot and must
never be exposed to GROSU. This preserves the read-only boundary — a leaked
token would allow the GROSU user to push images or mutate resources as the
robot.

### Key invariants in `endpoints/api/robot.py`

- **`include_token` must be `False` for GROSU.** Only org admins and
  full-access superusers (`SUPERUSERS_FULL_ACCESS`) may see robot tokens.
  The `OrgRobotList.get` and `OrgRobot.get` handlers gate `include_token`
  on `is_org_admin or is_full_access_superuser`; GROSU is neither, so
  it evaluates to `False`.
- **`include_permissions` should be `True` for GROSU.** The legacy robot
  manager UI requests `/api/v1/organization/<org>/robots?permissions=true&token=false`
  and depends on `teams` / `repositories` fields in the response. The
  `OrgRobotList.get` handler allows `include_permissions` when
  `is_org_admin`, `is_full_access_superuser`, **or** GROSU.
- **All write operations remain blocked.** Create (`PUT`), delete
  (`DELETE`), and regenerate (`POST .../regenerate`) endpoints are gated
  on `AdministerOrganizationPermission` or `allow_if_superuser_with_full_access()`
  and do not include `allow_if_global_readonly_superuser()`.

### Endpoint access matrix

| Endpoint | Org Admin | Full-Access Superuser | GROSU | Regular User |
|----------|-----------|----------------------|-------|--------------|
| `OrgRobotList` GET | metadata + token + permissions | metadata + token + permissions | metadata + permissions (no token) | metadata only |
| `OrgRobot` GET | metadata + token | metadata + token | metadata (no token) | Unauthorized |
| `OrgRobotPermissions` GET | permissions list | permissions list | permissions list | Unauthorized |
| Create / Delete / Regenerate | Yes | Yes | **Blocked** | Varies |

### Why this matters for code changes

When modifying GROSU logic in `robot.py`, always preserve these invariants:

1. GROSU must **never** see `token` fields — they are write-equivalent credentials.
2. GROSU **must** see `teams` and `repositories` when `?permissions=true` is
   requested, or the legacy robot manager UI breaks.
3. Do not add `allow_if_global_readonly_superuser()` to any write endpoint
   (create, delete, regenerate).

This invariant was established in PR [#6740](https://github.com/quay/quay/pull/6740)
after a human reviewer identified that an initial fix inadvertently broke
`permissions=true` support for GROSU.

## App Token Access

Special handling for app tokens:

| Endpoint | Superuser | Global Readonly | Regular User |
|----------|-----------|-----------------|--------------|
| List tokens | All tokens | All tokens | Own tokens only |
| Get token | Any token | Any token | Own tokens only |
| Create/Delete | Yes | No | Own tokens only |

## Testing

```bash
# Test read access (should work)
curl -s -b cookies.txt "http://localhost:8080/api/v1/repository/private/repo"

# Test v2 access
TOKEN=$(curl -s -u quayadmin:password "http://localhost:8080/v2/auth?service=localhost:8080" | jq -r '.token')
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/v2/_catalog"

# Test write blocking (should return 403/insufficient_scope)
curl -s -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"repository": "test", "visibility": "private"}' \
  "http://localhost:8080/api/v1/repository"
```

## Adding Global Readonly Support to New Endpoints

1. For read endpoints, add `allow_for_global_readonly_superuser=True` to decorator
2. For write endpoints, no changes needed (blocked by default)
3. Add tests in `endpoints/api/test/test_global_readonly_superuser.py`
