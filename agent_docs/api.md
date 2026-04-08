# API & Authentication

## API Architecture

**API v1** (`endpoints/api/`): REST API for UI and programmatic access
- Flask-based with resource decorators
- Session-based auth with CSRF tokens
- Endpoints return JSON

**API v2** (`endpoints/v2/`): OCI/Docker Registry Protocol
- JWT bearer token authentication
- Implements Docker Registry HTTP API V2
- Scope-based access control

## Testing API v1 (Session Auth)

```bash
# 1. Get CSRF token and establish session
CSRF_TOKEN=$(curl -s -c cookies.txt -b cookies.txt "http://localhost:8080/csrf_token" | jq -r '.csrf_token')

# 2. Sign in
curl -s -c cookies.txt -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"username": "admin", "password": "password"}' \
  "http://localhost:8080/api/v1/signin"

# 3. Use session cookies for API calls
curl -s -b cookies.txt "http://localhost:8080/api/v1/user/"
```

**Note:** Basic auth does NOT work with local dev for API v1.

## Testing API v2 (JWT Bearer Tokens)

```bash
# Get bearer token
TOKEN=$(curl -s -u username:password "http://localhost:8080/v2/auth?service=localhost:8080" | jq -r '.token')

# Use for v2 calls
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8080/v2/_catalog"

# With specific scope
TOKEN=$(curl -s -u username:password \
  "http://localhost:8080/v2/auth?service=localhost:8080&scope=repository:namespace/repo:pull" \
  | jq -r '.token')
```

## Adding API v1 Endpoints

1. Add endpoint to file in `endpoints/api/`
2. Use appropriate decorators:
   ```python
   from endpoints.api import resource, nickname, require_repo_read

   @resource('/v1/repository/<namespace>/<repository>/example')
   class RepositoryExample(RepositoryParamResource):
       @require_repo_read(allow_for_global_readonly_superuser=True)
       @nickname('getExample')
       def get(self, namespace, repository):
           # Implementation
   ```
3. Create model interface in `*_models_interface.py`
4. Implement model in `*_models_pre_oci.py`
5. Add tests in `endpoints/api/test/` or `test/`

## Permission Decorators

```python
# Repository permissions
@require_repo_read(allow_for_global_readonly_superuser=True)
@require_repo_write
@require_repo_admin

# User permissions
@require_user_admin
@require_fresh_login

# Superuser
@require_scope(scopes.SUPERUSER)
```

## Key Files

- `endpoints/api/__init__.py` - Core API setup, helper functions
- `endpoints/decorators.py` - Permission decorators
- `endpoints/exception.py` - API exceptions (Unauthorized, NotFound, etc.)
- `auth/permissions.py` - Permission classes
