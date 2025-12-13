# Backend Architecture

## Overview

Quay's backend is a Flask application serving multiple protocols:

- **REST API** (`/api/v1/`) - Web UI and external integrations
- **Docker Registry v2** (`/v2/`) - OCI Distribution Spec for `docker push/pull`
- **OAuth** (`/oauth/`) - Authentication flows

The application is defined in `app.py` and uses Flask blueprints for modular endpoint organization.

## Application Structure

### Initialization Flow

1. Flask app created with configuration from `config.py` or `test/testconfig.py`
2. Features loaded from config via `features.import_features()`
3. Extensions initialized: Flask-Login, Flask-Principal, Flask-Mail
4. Database configured via `database.configure()`
5. Registry and security scan models configured
6. Blueprints registered for each protocol

See: `app.py` (Flask app initialization through `database.configure()`)

### Request Lifecycle

Every request gets a unique ID via `RequestWithId` class. Before/after hooks handle:

- Debug logging with request ID
- Sensitive data filtering (passwords, tokens)
- Config digest tracking

See: `app.py`: `RequestWithId` class, `_request_start()`, `_request_end()`

## REST API (`endpoints/api/`)

### Endpoint Registration

Endpoints extend `ApiResource` (Flask-RESTful) and register via the `@resource` decorator:

| Pattern | Description |
|---------|-------------|
| `@resource('/v1/path')` | Register endpoint URL |
| `@show_if(feature)` | Conditionally show endpoint |
| `@hide_if(feature)` | Conditionally hide endpoint |

See: `endpoints/api/__init__.py`: `resource()`, `show_if()`, `hide_if()`

### Base Classes

| Class | Purpose |
|-------|---------|
| `ApiResource` | Base class with `check_anon_protection`, `check_readonly` decorators |
| `RepositoryParamResource` | Adds `parse_repository_name` for repo-scoped endpoints |

See: `endpoints/api/__init__.py`: `ApiResource`, `RepositoryParamResource`

### Request Handling Decorators

| Decorator | Purpose |
|-----------|---------|
| `@validate_json_request('Schema')` | JSON schema validation |
| `@query_param(name, help, type)` | Define query parameters |
| `@parse_args()` | Parse defined query params into `parsed_args` kwarg |
| `@page_support()` | Add pagination with `next_page` token |
| `@nickname('name')` | OpenAPI operation ID |
| `@deprecated()` | Add Deprecation header |

See: `endpoints/api/__init__.py`: `query_param()`, `page_support()`, `parse_args()`, `validate_json_request()`, `deprecated()`

### Example Endpoint Structure

Endpoints define JSON schemas as class attributes and use decorators for auth/validation.
See: `endpoints/api/repository.py`: `RepositoryList` class

## Authentication & Authorization

### Permission Decorators

| Decorator | Scope | Notes |
|-----------|-------|-------|
| `@require_repo_read()` | `READ_REPO` | Allows public repos |
| `@require_repo_write()` | `WRITE_REPO` | |
| `@require_repo_admin()` | `ADMIN_REPO` | |
| `@require_user_read()` | `READ_USER` | |
| `@require_user_admin()` | `ADMIN_USER` | |
| `@require_scope(scope)` | Custom OAuth scope | |
| `@require_fresh_login` | - | Requires recent auth |

See: `endpoints/api/__init__.py`: `require_repo_read()`, `require_repo_write()`, `require_repo_admin()`, `require_user_read()`, `require_user_admin()`, `require_fresh_login()`, `require_scope()`

### Superuser Access Helpers

| Function | Use Case |
|----------|----------|
| `allow_if_superuser()` | Basic superuser panel access |
| `allow_if_superuser_with_full_access()` | Bypass normal permissions (requires SUPERUSERS_FULL_ACCESS) |
| `allow_if_global_readonly_superuser()` | Read-only superuser access |

See: `endpoints/api/__init__.py`: `allow_if_superuser()`, `allow_if_superuser_with_full_access()`, `allow_if_global_readonly_superuser()`

### Authentication Processing

API endpoints use OAuth token validation via `process_oauth` decorator applied globally to the API blueprint.

See: `endpoints/api/__init__.py`: `api.decorators` list, `auth/decorators.py`

## Docker Registry v2 (`endpoints/v2/`)

Implements OCI Distribution Spec for container image push/pull operations.

### Endpoint Table

| Route | Methods | Handler | Purpose |
|-------|---------|---------|---------|
| `/v2/` | GET | `v2_support_enabled` | Version check |
| `/v2/<repo>/blobs/<digest>` | GET, HEAD | `blob.py` | Blob download |
| `/v2/<repo>/blobs/uploads/` | POST, PATCH, PUT | `blob.py` | Blob upload |
| `/v2/<repo>/manifests/<ref>` | GET, PUT, DELETE | `manifest.py` | Manifest operations |
| `/v2/<repo>/tags/list` | GET | `tag.py` | Tag listing |
| `/v2/_catalog` | GET | `catalog.py` | Repository catalog |
| `/v2/<repo>/referrers/<digest>` | GET | `referrers.py` | OCI referrers |

See: `endpoints/v2/` directory

### V2 Authentication

Uses JWT-based authentication via `@process_registry_jwt_auth()` decorator.

See: `auth/registry_jwt_auth.py`, `endpoints/v2/v2auth.py`

### V2 Error Handling

Errors extend `V2RegistryException` and return OCI-compliant error responses:

| Error | HTTP Code |
|-------|-----------|
| `NameUnknown` | 404 |
| `ManifestUnknown` | 404 |
| `BlobUnknown` | 404 |
| `Unauthorized` | 401 |
| `Unsupported` | 415 |

See: `endpoints/v2/errors.py`

### V2 Permission Decorators

Similar to API but with OCI scope format:

| Decorator | Scopes |
|-----------|--------|
| `@require_repo_read()` | `["pull"]` |
| `@require_repo_write()` | `["pull", "push"]` |
| `@require_repo_admin()` | `["pull", "push"]` |

See: `endpoints/v2/__init__.py`: `require_repo_read()`, `require_repo_write()`, `require_repo_admin()`

## Common Decorators (`endpoints/decorators.py`)

| Decorator | Purpose |
|-----------|---------|
| `@parse_repository_name()` | Parse `namespace/repo` from path |
| `@inject_registry_model()` | Inject appropriate registry model (OCIModel or ProxyModel) |
| `@check_readonly` | Block non-GET in read-only mode |
| `@check_pushes_disabled` | Block pushes when disabled |
| `@check_anon_protection` | Require auth when anonymous access disabled |
| `@check_region_blacklisted()` | Geo-IP blocking |
| `@check_repository_state` | Handle mirror/readonly repo states |
| `@anon_allowed` | Mark method as allowing anonymous access |
| `@readonly_call_allowed` | Allow non-GET in read-only mode |

See: `endpoints/decorators.py`

## Error Handling (`endpoints/exception.py`)

API errors use RFC 7807 format via `ApiException` base class.

| Exception | HTTP Code | Error Type |
|-----------|-----------|------------|
| `InvalidRequest` | 400 | `invalid_request` |
| `Unauthorized` | 401/403 | `invalid_token` / `insufficient_scope` |
| `FreshLoginRequired` | 401 | `fresh_login_required` |
| `NotFound` | 404 | `not_found` |
| `ExceedsLicenseException` | 402 | `exceeds_license` |
| `DownstreamIssue` | 520 | `downstream_issue` |
| `ExternalServiceError` | 520 | `external_service_timeout` |

See: `endpoints/exception.py`

## Data Layer Integration

Endpoints interact with data through abstraction layers:

| Layer | Purpose |
|-------|---------|
| `data/registry_model/` | High-level registry operations (OCIModel, ProxyModel) |
| `data/model/` | Business logic and database queries |
| `data/database.py` | SQLAlchemy/PeeWee model definitions |
| `model_cache` | In-memory caching for performance |

Audit logging via `log_action()` function records user actions.

See: `endpoints/api/__init__.py`: `log_action()`, `data/registry_model/registry_oci_model.py`

For detailed database documentation, see: `docs/agents/database.md`

## Testing

```bash
# API endpoint tests
TEST=true PYTHONPATH="." pytest endpoints/api/test/ -v

# Registry v2 tests
TEST=true PYTHONPATH="." pytest endpoints/v2/test/ -v

# Run with coverage
TEST=true PYTHONPATH="." pytest --cov=endpoints endpoints/api/test/ -v
```

See: `test/` directory for integration tests, `endpoints/*/test/` for unit tests

For test patterns and examples, see: `docs/agents/testing.md`
