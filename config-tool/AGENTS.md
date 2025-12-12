# Config Tool - Developer Agent Context

## Project Overview

Go-based CLI tool for validating and editing Quay configuration files. Provides schema-based validation, an interactive config editor UI, and code generation for field group definitions.

## Tech Stack

- **Language**: Go 1.21+
- **CLI Framework**: Cobra
- **Validation**: go-playground/validator
- **Build**: Make, Docker/Podman

## Core Workflow

```bash
cd config-tool/

# Build and generate
go install ./...              # Install CLI
make generate                 # Generate field group code

# Test
make test                     # Run all tests
go test ./pkg/lib/fieldgroups/...  # Test specific field groups

# Run
./config-tool validate -c /path/to/config
./config-tool editor -c /path/to/config -p password  # Web UI on :8080
```

## Directory Structure

```
config-tool/
├── cmd/config-tool/main.go   # Entrypoint
├── commands/                 # CLI commands (Cobra)
│   ├── root.go, validate.go, print.go, editor.go
├── pkg/lib/
│   ├── config/               # Config loading and validation
│   ├── editor/               # Web-based config editor
│   ├── fieldgroups/          # Config field definitions (see below)
│   └── shared/               # Common validators and types
├── utils/generate/           # Field group generator
└── testdata/                 # Test fixtures
```

## Field Groups

Each configuration section is a "field group" in `pkg/lib/fieldgroups/`. Key groups:

| Field Group | Config Keys |
|-------------|-------------|
| `database` | DB_URI, DB_CONNECTION_ARGS |
| `distributedstorage` | DISTRIBUTED_STORAGE_CONFIG |
| `hostsettings` | SERVER_HOSTNAME, PREFERRED_URL_SCHEME |
| `redis` | BUILDLOGS_REDIS, USER_EVENTS_REDIS |
| `securityscanner` | SECURITY_SCANNER_*, FEATURE_SECURITY_SCANNER |

### Field Group Structure

Each field group has three files:
```
fieldgroup/
├── fieldgroup.go           # Struct definition + constructor
├── fieldgroup_fields.go    # Fields() method listing config keys
└── fieldgroup_validator.go # Validate() method with custom logic
```

**Reference implementation**: See `pkg/lib/fieldgroups/redis/` for a complete working example.

### Adding a New Field

1. Add field to struct in `fieldgroup.go` with json/yaml/validate tags
2. Update `fieldgroup_fields.go` if adding a new top-level key
3. Add custom validation in `fieldgroup_validator.go` if needed
4. Run `make generate`
5. Add tests, update corresponding Python config in `config.py`

### Creating a New Field Group

1. Create directory: `pkg/lib/fieldgroups/myconfig/`
2. Create the three files following the pattern in `redis/`
3. Register in `pkg/lib/config/config.go` by adding to `NewConfig()`
4. Run `make generate` and add tests

## Validation

Uses go-playground/validator tags: `required`, `url`, `oneof=a b c`, `email`, `min=`, `max=`

Common shared validators in `pkg/lib/shared/validators.go`:

| Validator | Purpose |
|-----------|---------|
| `ValidateRequiredString` | Required string field |
| `ValidateIsOneOfString` | Enum validation |
| `ValidateHostIsReachable` | Network connectivity check |
| `ValidateRedisConnection` | Redis connectivity |
| `ValidateDatabaseConnection` | Database connectivity |

## Integration with Quay

- Config-tool validates `config.yaml` before Quay starts
- Field groups must match Python config schema in `config.py`
- Quay Operator uses config-tool for configuration validation
