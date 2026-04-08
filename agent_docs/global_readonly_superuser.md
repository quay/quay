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
