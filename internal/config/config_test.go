package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const minimalValidYAML = `
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
SECRET_KEY: "abc123"
DATABASE_SECRET_KEY: "def456"
`

func TestParseMinimalValid(t *testing.T) {
	cfg, err := Parse([]byte(minimalValidYAML))
	require.NoError(t, err)

	assert.Equal(t, "quay.example.com", cfg.ServerHostname)
	assert.Equal(t, "https", cfg.PreferredURLScheme)
	assert.Equal(t, "postgresql://user:pass@db:5432/quay", cfg.DBURI)
	require.NotNil(t, cfg.BuildlogsRedis)
	assert.Equal(t, "redis", cfg.BuildlogsRedis.Host)
	assert.Equal(t, "abc123", cfg.SecretKey)
}

func TestParseDefaults(t *testing.T) {
	cfg, err := Parse([]byte("SERVER_HOSTNAME: test\n"))
	require.NoError(t, err)

	assert.Equal(t, "http", cfg.PreferredURLScheme)
	assert.Equal(t, "Red Hat Quay", cfg.RegistryTitle)
	assert.Equal(t, "Database", cfg.AuthenticationType)
	require.NotNil(t, cfg.FeatureDirectLogin)
	assert.True(t, *cfg.FeatureDirectLogin)
}

func TestParseExplicitFalseNotOverridden(t *testing.T) {
	yaml := "FEATURE_DIRECT_LOGIN: false\n"
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	require.NotNil(t, cfg.FeatureDirectLogin)
	assert.False(t, *cfg.FeatureDirectLogin)
}

func TestParseUnknownFields(t *testing.T) {
	yaml := `
SERVER_HOSTNAME: test
SOME_CUSTOM_KEY: value
ANOTHER_UNKNOWN: 42
`
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	assert.Len(t, cfg.Extra, 2)
	assert.Equal(t, "value", cfg.Extra["SOME_CUSTOM_KEY"])
}

func TestParseStorageTuple(t *testing.T) {
	yaml := `
DISTRIBUTED_STORAGE_CONFIG:
  local:
    - LocalStorage
    - storage_path: /data
  s3:
    - S3Storage
    - s3_bucket: my-bucket
      s3_access_key: AKIA123
`
	cfg, err := Parse([]byte(yaml))
	require.NoError(t, err)

	require.Len(t, cfg.DistributedStorageConfig, 2)

	local, ok := cfg.DistributedStorageConfig["local"]
	require.True(t, ok, "missing 'local' storage entry")
	assert.Equal(t, "LocalStorage", local.Driver)
	assert.Equal(t, "/data", local.Params["storage_path"])

	s3, ok := cfg.DistributedStorageConfig["s3"]
	require.True(t, ok, "missing 's3' storage entry")
	assert.Equal(t, "S3Storage", s3.Driver)
	assert.Equal(t, "my-bucket", s3.Params["s3_bucket"])
}

func TestParseMalformedYAML(t *testing.T) {
	_, err := Parse([]byte(":\n  [invalid yaml"))
	assert.Error(t, err)
}

func TestLoadDirectory(t *testing.T) {
	dir := t.TempDir()
	err := os.WriteFile(filepath.Join(dir, "config.yaml"), []byte(minimalValidYAML), 0o644)
	require.NoError(t, err)

	cfg, err := Load(dir)
	require.NoError(t, err)
	assert.Equal(t, "quay.example.com", cfg.ServerHostname)
}

func FuzzParse(f *testing.F) {
	// Seed with known-good configs and interesting edge cases.
	f.Add([]byte(minimalValidYAML))
	f.Add([]byte("{}"))
	f.Add([]byte(""))
	f.Add([]byte("DISTRIBUTED_STORAGE_CONFIG:\n  x:\n    - LocalStorage\n    - storage_path: /data"))
	f.Add([]byte("BUILDLOGS_REDIS:\n  host: r\n  port: 0"))
	f.Add([]byte("SERVER_HOSTNAME: [unterminated"))
	f.Add([]byte(":\n  [invalid yaml"))
	f.Add([]byte("DEFAULT_TAG_EXPIRATION: 999999999999999999999w"))
	f.Add([]byte("PREFERRED_URL_SCHEME: ftp\nSERVER_HOSTNAME: x\nDB_URI: mongo://x"))

	f.Fuzz(func(t *testing.T, data []byte) {
		// Parse must never panic — errors are fine.
		cfg, err := Parse(data)
		if err != nil {
			return
		}
		// If it parsed, validation must also not panic.
		_ = Validate(t.Context(), cfg, ValidateOptions{Mode: "offline"})
	})
}

func FuzzDurationPattern(f *testing.F) {
	f.Add("2w")
	f.Add("0s")
	f.Add("forever")
	f.Add("")
	f.Add("999999999999999999999w")
	f.Add("2w3d")
	f.Add("w")
	f.Add("42")
	f.Add("2 w")

	f.Fuzz(func(_ *testing.T, s string) {
		// Must never panic.
		_ = durationPattern.MatchString(s)
	})
}

func TestLoadExistingTestdata(t *testing.T) {
	// Validate against the existing config-tool testdata if available.
	path := filepath.Join("..", "..", "config-tool", "testdata", "config-bundle", "config.yaml")
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Skip("config-tool testdata not found")
	}

	cfg, err := Load(path)
	require.NoError(t, err)

	assert.Equal(t, "quay", cfg.ServerHostname)
	assert.NotEmpty(t, cfg.DBURI)
	assert.NotNil(t, cfg.BuildlogsRedis)
}
