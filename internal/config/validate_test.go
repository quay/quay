package config

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestValidateEmptyConfig(t *testing.T) {
	cfg, err := Parse([]byte("{}"))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})

	requiredMissing := []string{
		"SECRET_KEY",
		"DATABASE_SECRET_KEY",
		"SERVER_HOSTNAME",
		"DB_URI",
		"DISTRIBUTED_STORAGE_CONFIG",
		"BUILDLOGS_REDIS",
		"USER_EVENTS_REDIS",
		"DISTRIBUTED_STORAGE_PREFERENCE",
		"TAG_EXPIRATION_OPTIONS",
	}

	errFields := make(map[string]bool)
	for _, e := range errs {
		if e.Severity == SeverityError {
			errFields[e.Field] = true
		}
	}

	for _, field := range requiredMissing {
		assert.True(t, errFields[field], "expected required-field error for %s", field)
	}
}

func TestValidateValidConfig(t *testing.T) {
	cfg, err := Parse([]byte(minimalValidYAML))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.False(t, HasErrors(errs), "unexpected errors: %v", errs)
}

func TestValidateInvalidEnums(t *testing.T) {
	yaml := minimalValidYAML + `
REGISTRY_STATE: broken
`
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "REGISTRY_STATE"), "expected error for invalid REGISTRY_STATE enum")
}

func TestValidateInvalidPreferredURLScheme(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML, "PREFERRED_URL_SCHEME: https", "PREFERRED_URL_SCHEME: ftp", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "PREFERRED_URL_SCHEME"), "expected error for invalid PREFERRED_URL_SCHEME")
}

func TestValidateInvalidDBURI(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML, "DB_URI: postgresql://user:pass@db:5432/quay", "DB_URI: mongo://localhost/quay", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "DB_URI"), "expected error for invalid DB_URI prefix")
}

func TestValidateStorageCrossReference(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML, "- default", "- nonexistent", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "DISTRIBUTED_STORAGE_PREFERENCE"), "expected cross-reference error for undefined storage preference")
}

func TestValidateInvalidAuthenticationType(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML, "AUTHENTICATION_TYPE: Database", "AUTHENTICATION_TYPE: Database!", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "AUTHENTICATION_TYPE"), "expected error for invalid AUTHENTICATION_TYPE")
}

func TestValidateInvalidTagExpiration(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML, "DEFAULT_TAG_EXPIRATION: 2w", "DEFAULT_TAG_EXPIRATION: forever", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "DEFAULT_TAG_EXPIRATION"), "expected error for invalid DEFAULT_TAG_EXPIRATION format")
}

func TestValidateInvalidTagExpirationOption(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML,
		"TAG_EXPIRATION_OPTIONS:\n  - 0s\n  - 1d\n  - 2w",
		"TAG_EXPIRATION_OPTIONS:\n  - 2w\n  - invalid", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "TAG_EXPIRATION_OPTIONS"), "expected error for invalid TAG_EXPIRATION_OPTIONS item")
}

func TestValidateTagExpirationNotInOptions(t *testing.T) {
	yaml := strings.Replace(minimalValidYAML,
		"TAG_EXPIRATION_OPTIONS:\n  - 0s\n  - 1d\n  - 2w",
		"TAG_EXPIRATION_OPTIONS:\n  - 0s\n  - 1d", 1)
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldWarning(errs, "DEFAULT_TAG_EXPIRATION"), "expected warning for DEFAULT_TAG_EXPIRATION not in TAG_EXPIRATION_OPTIONS")
}

func TestValidateInvalidSecurityEndpoint(t *testing.T) {
	yaml := minimalValidYAML + `
SECURITY_SCANNER_V4_ENDPOINT: not-a-url
`
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	assert.True(t, hasFieldError(errs, "SECURITY_SCANNER_V4_ENDPOINT"), "expected error for invalid SECURITY_SCANNER_V4_ENDPOINT")
}

func TestValidateRedisHostRequired(t *testing.T) {
	yaml := `
SERVER_HOSTNAME: test
DB_URI: postgresql://u:p@h/d
AUTHENTICATION_TYPE: Database
SECRET_KEY: testkey
DATABASE_SECRET_KEY: testdbkey
BUILDLOGS_REDIS:
  port: 6379
USER_EVENTS_REDIS:
  host: redis
DISTRIBUTED_STORAGE_CONFIG:
  default:
    - LocalStorage
    - storage_path: /data
DISTRIBUTED_STORAGE_PREFERENCE:
  - default
DEFAULT_TAG_EXPIRATION: 2w
TAG_EXPIRATION_OPTIONS:
  - 2w
`
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	found := false
	for _, e := range errs {
		if e.Field == "BUILDLOGS_REDIS" && e.Severity == SeverityError && strings.Contains(e.Message, "host") {
			found = true
		}
	}
	assert.True(t, found, "expected error for BUILDLOGS_REDIS missing host")
}

func TestValidateSecretKeysRequired(t *testing.T) {
	// minimalValidYAML minus SECRET_KEY and DATABASE_SECRET_KEY
	yaml := `
PREFERRED_URL_SCHEME: https
SERVER_HOSTNAME: quay.example.com
DB_URI: postgresql://user:pass@db:5432/quay
AUTHENTICATION_TYPE: Database
BUILDLOGS_REDIS:
  host: redis
  port: 6379
USER_EVENTS_REDIS:
  host: redis
  port: 6379
DISTRIBUTED_STORAGE_CONFIG:
  default:
    - LocalStorage
    - storage_path: /data
DISTRIBUTED_STORAGE_PREFERENCE:
  - default
DEFAULT_TAG_EXPIRATION: 2w
TAG_EXPIRATION_OPTIONS:
  - 0s
  - 1d
  - 2w
`
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	errs := Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})

	for _, key := range []string{"SECRET_KEY", "DATABASE_SECRET_KEY"} {
		assert.True(t, hasFieldError(errs, key), "expected required-field error for %s", key)
	}
}

// hasFieldError checks if any validation error has the given field and error severity.
func hasFieldError(errs []ValidationError, field string) bool {
	for _, e := range errs {
		if e.Field == field && e.Severity == SeverityError {
			return true
		}
	}
	return false
}

// hasFieldWarning checks if any validation error has the given field and warning severity.
func hasFieldWarning(errs []ValidationError, field string) bool {
	for _, e := range errs {
		if e.Field == field && e.Severity == SeverityWarning {
			return true
		}
	}
	return false
}
