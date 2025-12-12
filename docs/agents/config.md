# Configuration Guide

## Overview

Quay configuration is managed through `config.yaml` (runtime) and validated by `config-tool/` (Go).

| File | Purpose |
|------|---------|
| `config.py` | Python config defaults (customer-facing) |
| `features/__init__.py` | Feature flag loading |
| `config-tool/pkg/lib/fieldgroups/` | Go validation schemas |
| `util/config/schema.py` | Schema docs and INTERNAL_ONLY_PROPERTIES |

## Config Categories

Quay has three categories of configuration:

| Category | In DefaultConfig? | When to Use |
|----------|-------------------|-------------|
| Customer-facing | Yes | Downstream Quay deployments, documented |
| Internal-only | Yes (marked `[QUAY.IO]`) | In DefaultConfig but hidden from customer docs |
| Runtime-only | No | Quay.io infrastructure, accessed via `app.config.get()` |

## Adding a Customer-Facing Config Field

For configs exposed to downstream Quay customers:

### Step 1: Add default in config.py

Add to the `DefaultConfig` class:

```python
class DefaultConfig(ImmutableConfig):
    # Description of what this config controls
    MY_NEW_CONFIG: Optional[str] = "default_value"
```

See: `config.py`: `DefaultConfig` class

### Step 2: Add validation in config-tool (if complex)

For nested configs requiring validation, create a fieldgroup. See "Adding a Complex Config Field" below.

### Step 3: Expose to frontend (if needed)

Add to `CLIENT_WHITELIST` (only for non-secret values):

```python
CLIENT_WHITELIST = [
    "MY_NEW_CONFIG",
]
```

See: `config.py`: `CLIENT_WHITELIST`

## Adding a Quay.io-Only Config

For Quay.io infrastructure-specific configs (analytics, billing, worker tuning):

### Option 1: Runtime-only (not in DefaultConfig)

Simply access via `app.config.get()` without adding to DefaultConfig:

```python
# No entry in config.py needed
value = app.config.get("QUAYIO_SPECIFIC_CONFIG")
poll_period = app.config.get("MY_WORKER_POLL_PERIOD", 300)
```

Examples of runtime-only configs:

- `GOOGLE_TAGMANAGER_KEY`, `GOOGLE_ANALYTICS_KEY`
- `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`
- `STRIPE_SECRET_KEY`
- Worker poll periods: `QUOTA_REGISTRY_SIZE_POLL_PERIOD`, etc.

See: `endpoints/common.py`, `workers/worker.py` for runtime config access patterns

### Option 2: Internal-only (in DefaultConfig but hidden)

For configs that need a default but shouldn't be in customer docs:

1. Add to DefaultConfig with safe default
2. Add to `INTERNAL_ONLY_PROPERTIES` in schema

```python
# util/config/schema.py
INTERNAL_ONLY_PROPERTIES = {
    "BILLING_TYPE",
    "ANALYTICS_TYPE",
    "MY_INTERNAL_CONFIG",  # Add here
}
```

See: `util/config/schema.py` (INTERNAL_ONLY_PROPERTIES)

## Adding a Feature Flag

### Step 1: Define in config.py

Add to `DefaultConfig` with `FEATURE_` prefix:

```python
class DefaultConfig(ImmutableConfig):
    # Feature Flag: Description of what this enables
    FEATURE_MY_FEATURE = False  # Default to False for gradual rollout
```

See: `config.py`: `DefaultConfig` class (`FEATURE_*` attributes)

### Step 2: Use in Python code

After app initialization, access via the `features` module:

```python
import features

if features.MY_FEATURE:
    # Feature-specific logic
    pass
```

See: `features/__init__.py`: `import_features()`, `app.py`: `features.import_features(app.config)`

### Frontend access

All feature flags are automatically sent to frontend via `/config` endpoint.

## Adding a Complex Config Field (with validation)

For config fields that need schema validation in the config editor:

1. Add default in `config.py` DefaultConfig class
2. Create a fieldgroup in `config-tool/pkg/lib/fieldgroups/`
3. Register the fieldgroup in `config-tool/pkg/lib/config/config.go`

See: `config-tool/AGENTS.md` for detailed fieldgroup creation instructions

## Environment-Specific Behavior

For Quay.io vs downstream differences, use hostname checks:

```python
if app.config["SERVER_HOSTNAME"].find("quay.io") >= 0:
    # Quay.io-specific behavior
```

Or use `RED_HAT_QUAY` environment variable for branding:

```python
if os.environ.get("RED_HAT_QUAY", False):
    # Red Hat Quay branding
```

See: `config.py`, `endpoints/api/__init__.py`: `verify_not_prod()` decorator

## Removing a Config Field

1. Remove from `config.py` DefaultConfig class (if present)
2. Remove from `CLIENT_WHITELIST` if present
3. Remove from `INTERNAL_ONLY_PROPERTIES` if present
4. Remove fieldgroup from `config-tool/pkg/lib/fieldgroups/` if exists
5. Remove registration from `config-tool/pkg/lib/config/config.go`
6. Search codebase for usages and remove

## Testing Config Changes

```bash
# Validate config file
./config-tool validate -c /path/to/config.yaml

# Override config in tests
QUAY_OVERRIDE_CONFIG='{"MY_NEW_CONFIG": "test_value"}' pytest ...
```

## Local Development

Edit `local-dev/config/config.yaml` for local settings.

See: `local-dev/`

Full config-tool documentation: `config-tool/AGENTS.md`

For test patterns (including mocking feature flags), see: `docs/agents/testing.md`
