package migrate

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/go-jose/go-jose/v4"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/registry/jwtauth"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type registryKeyFixture struct {
	dbPath    string
	configDir string
	targetDir string
	key       *rsa.PrivateKey
	kid       string
	cfg       *config.Config
}

func TestLoadApprovedRegistryJWTSigningKeyRejectsMismatchedMaterial(t *testing.T) {
	tests := []struct {
		name    string
		mutate  func(*testing.T, *registryKeyFixture)
		wantErr string
	}{
		{
			name: "private key and kid",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				writeCopyTestFile(t, filepath.Join(fixture.configDir, legacyKeyIDName), []byte("different-kid"), 0o600)
			},
			wantErr: "private key does not match key ID",
		},
		{
			name: "jwk key id",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				jwk := marshalTestJWK(t, &fixture.key.PublicKey, "different-kid")
				execRegistryKeyFixture(t, fixture, `UPDATE servicekey SET jwk = ?`, jwk)
			},
			wantErr: "JWK has mismatched key ID",
		},
		{
			name: "private key and jwk",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				otherKey, err := rsa.GenerateKey(rand.Reader, 2048)
				require.NoError(t, err)
				jwk := marshalTestJWK(t, &otherKey.PublicKey, fixture.kid)
				execRegistryKeyFixture(t, fixture, `UPDATE servicekey SET jwk = ?`, jwk)
			},
			wantErr: "private key does not match approved database JWK",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fixture := newRegistryKeyFixture(t)
			tt.mutate(t, fixture)

			_, _, err := loadApprovedRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.configDir, fixture.cfg, nil)

			require.Error(t, err)
			assert.Contains(t, err.Error(), tt.wantErr)
		})
	}
}

func TestLoadApprovedRegistryJWTSigningKeyRequiresApprovedUnexpiredKey(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*testing.T, *registryKeyFixture)
	}{
		{
			name: "unapproved",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				execRegistryKeyFixture(t, fixture, `DELETE FROM servicekeyapproval`)
			},
		},
		{
			name: "expired",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				execRegistryKeyFixture(t, fixture, `UPDATE servicekey SET expiration_date = datetime('now', '-1 second')`)
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fixture := newRegistryKeyFixture(t)
			tt.mutate(t, fixture)

			_, _, err := loadApprovedRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.configDir, fixture.cfg, nil)

			require.Error(t, err)
			assert.Contains(t, err.Error(), "not approved and unexpired")
		})
	}
}

func TestLoadApprovedRegistryJWTSigningKeyUsesConfiguredLegacyPaths(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	configuredKey := filepath.Join(fixture.configDir, "keys", "active.pem")
	configuredKID := filepath.Join(fixture.configDir, "keys", "active.kid")
	require.NoError(t, os.MkdirAll(filepath.Dir(configuredKey), 0o750))
	require.NoError(t, jwtauth.WritePrivateKey(configuredKey, fixture.key))
	writeCopyTestFile(t, configuredKID, []byte(fixture.kid+"\n"), 0o600)
	fixture.cfg.InstanceServiceKeyLocation = "/conf/stack/keys/active.pem"
	fixture.cfg.InstanceServiceKeyKIDLocation = "/conf/stack/keys/active.kid"

	key, kid, err := loadApprovedRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.configDir, fixture.cfg, nil)

	require.NoError(t, err)
	assert.Equal(t, fixture.kid, kid)
	assert.True(t, jwtauth.PublicKeysEqual(&fixture.key.PublicKey, &key.PublicKey))
}

func TestLoadApprovedRegistryJWTSigningKeyMapsContainerStackPath(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	configuredKey := filepath.Join(fixture.configDir, "keys", "active.pem")
	configuredKID := filepath.Join(fixture.configDir, "keys", "active.kid")
	require.NoError(t, os.MkdirAll(filepath.Dir(configuredKey), 0o750))
	require.NoError(t, jwtauth.WritePrivateKey(configuredKey, fixture.key))
	writeCopyTestFile(t, configuredKID, []byte(fixture.kid), 0o600)
	fixture.cfg.InstanceServiceKeyLocation = "/quay-registry/conf/stack/keys/active.pem"
	fixture.cfg.InstanceServiceKeyKIDLocation = "/quay-registry/conf/stack/keys/active.kid"

	key, kid, err := loadApprovedRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.configDir, fixture.cfg, nil)

	require.NoError(t, err)
	assert.Equal(t, fixture.kid, kid)
	assert.True(t, jwtauth.PublicKeysEqual(&fixture.key.PublicKey, &key.PublicKey))
}

func TestLoadApprovedRegistryJWTSigningKeyReadsContainerDefaults(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	privatePath := filepath.Join(fixture.configDir, legacyPrivateKeyName)
	kidPath := filepath.Join(fixture.configDir, legacyKeyIDName)
	privateBytes, err := os.ReadFile(privatePath) //nolint:gosec // test fixture path
	require.NoError(t, err)
	kidBytes, err := os.ReadFile(kidPath) //nolint:gosec // test fixture path
	require.NoError(t, err)
	require.NoError(t, os.Remove(privatePath))
	require.NoError(t, os.Remove(kidPath))
	runner := &sourceMaterialRunner{outputs: map[string]string{
		filepath.Join(sourceContainerConf, legacyPrivateKeyName): string(privateBytes),
		filepath.Join(sourceContainerConf, legacyKeyIDName):      string(kidBytes),
	}}

	key, kid, err := loadApprovedRegistryJWTSigningKey(
		t.Context(), fixture.dbPath, fixture.configDir, fixture.cfg, runner,
	)

	require.NoError(t, err)
	assert.Equal(t, fixture.kid, kid)
	assert.True(t, jwtauth.PublicKeysEqual(&fixture.key.PublicKey, &key.PublicKey))
}

func TestLoadApprovedRegistryJWTSigningKeyRejectsMissingSourceMaterial(t *testing.T) {
	tests := []struct {
		name    string
		remove  string
		mutate  func(*testing.T, *registryKeyFixture)
		wantErr string
	}{
		{name: "private key", remove: legacyPrivateKeyName, wantErr: "load source registry JWT private key"},
		{name: "key id", remove: legacyKeyIDName, wantErr: "read source registry JWT key ID"},
		{
			name: "empty key id",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				writeCopyTestFile(t, filepath.Join(fixture.configDir, legacyKeyIDName), []byte(" \n"), 0o600)
			},
			wantErr: "key ID from",
		},
		{
			name: "invalid database jwk",
			mutate: func(t *testing.T, fixture *registryKeyFixture) {
				t.Helper()
				execRegistryKeyFixture(t, fixture, `UPDATE servicekey SET jwk = 'not-json'`)
			},
			wantErr: "parse approved source registry JWT JWK",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fixture := newRegistryKeyFixture(t)
			if tt.remove != "" {
				require.NoError(t, os.Remove(filepath.Join(fixture.configDir, tt.remove)))
			}
			if tt.mutate != nil {
				tt.mutate(t, fixture)
			}

			_, _, err := loadApprovedRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.configDir, fixture.cfg, nil)

			require.Error(t, err)
			assert.Contains(t, err.Error(), tt.wantErr)
			if tt.name == "empty key id" {
				assert.Contains(t, err.Error(), "is empty")
			}
		})
	}
}

func TestImportRegistryJWTKeyAcceptsMatchingExistingNativeKey(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	require.NoError(t, os.MkdirAll(fixture.targetDir, 0o750))
	targetPath := filepath.Join(fixture.targetDir, jwtauth.KeyFileName)
	require.NoError(t, jwtauth.WritePrivateKey(targetPath, fixture.key))
	migrator := &Migrator{DataDir: fixture.targetDir, Source: OMRSource{ConfigDir: fixture.configDir}}

	require.NoError(t, migrator.importRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.cfg, false))
}

func TestImportRegistryJWTKeyRejectsMismatchedExistingNativeKey(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	require.NoError(t, os.MkdirAll(fixture.targetDir, 0o750))
	otherKey, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	require.NoError(t, jwtauth.WritePrivateKey(filepath.Join(fixture.targetDir, jwtauth.KeyFileName), otherKey))
	migrator := &Migrator{DataDir: fixture.targetDir, Source: OMRSource{ConfigDir: fixture.configDir}}

	err = migrator.importRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.cfg, false)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "existing native registry JWT key does not match")
}

func TestImportRegistryJWTKeyDoesNotReplaceKeyAfterLoadFailure(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	require.NoError(t, os.MkdirAll(fixture.targetDir, 0o750))
	otherKey, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	targetPath := filepath.Join(fixture.targetDir, jwtauth.KeyFileName)
	require.NoError(t, jwtauth.WritePrivateKey(targetPath, otherKey))
	original, err := os.ReadFile(targetPath)
	require.NoError(t, err)
	require.NoError(t, os.Chmod(targetPath, 0o640))
	migrator := &Migrator{DataDir: fixture.targetDir, Source: OMRSource{ConfigDir: fixture.configDir}}

	err = migrator.importRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.cfg, true)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "insecure permissions")
	remaining, readErr := os.ReadFile(targetPath)
	require.NoError(t, readErr)
	assert.Equal(t, original, remaining)
}

func TestImportRegistryJWTKeyReplacesMismatchedKeyDuringResume(t *testing.T) {
	fixture := newRegistryKeyFixture(t)
	require.NoError(t, os.MkdirAll(fixture.targetDir, 0o750))
	otherKey, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	targetPath := filepath.Join(fixture.targetDir, jwtauth.KeyFileName)
	require.NoError(t, jwtauth.WritePrivateKey(targetPath, otherKey))
	migrator := &Migrator{DataDir: fixture.targetDir, Source: OMRSource{ConfigDir: fixture.configDir}}

	require.NoError(t, migrator.importRegistryJWTSigningKey(t.Context(), fixture.dbPath, fixture.cfg, true))
	loaded, err := jwtauth.LoadPrivateKey(targetPath)
	require.NoError(t, err)
	assert.True(t, jwtauth.PublicKeysEqual(&fixture.key.PublicKey, &loaded.PublicKey))
}

func newRegistryKeyFixture(t *testing.T) *registryKeyFixture {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay_sqlite.db")
	createCopyTestDB(t, dbPath)
	configDir := t.TempDir()
	key := seedCopyTestRegistryKey(t, dbPath, configDir)
	kid, err := jwtauth.KeyID(&key.PublicKey)
	require.NoError(t, err)
	return &registryKeyFixture{
		dbPath: dbPath, configDir: configDir, targetDir: t.TempDir(), key: key, kid: kid,
		cfg: &config.Config{Keys: config.Keys{
			InstanceServiceKeyService: config.DefaultInstanceServiceKeyService,
		}},
	}
}

func execRegistryKeyFixture(t *testing.T, fixture *registryKeyFixture, query string, args ...any) {
	t.Helper()
	db, err := dbcore.OpenSQLite(fixture.dbPath)
	require.NoError(t, err)
	defer db.Close()
	_, err = db.ExecContext(t.Context(), query, args...)
	require.NoError(t, err)
}

func marshalTestJWK(t *testing.T, key *rsa.PublicKey, kid string) string {
	t.Helper()
	data, err := json.Marshal(jose.JSONWebKey{Key: key, KeyID: kid, Algorithm: string(jose.RS256), Use: "sig"})
	require.NoError(t, err)
	return string(data)
}

func seedExistingSchemaRegistryKey(t *testing.T, dbPath, configDir string) {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	kid, err := jwtauth.KeyID(&key.PublicKey)
	require.NoError(t, err)
	require.NoError(t, jwtauth.WritePrivateKey(filepath.Join(configDir, legacyPrivateKeyName), key))
	writeCopyTestFile(t, filepath.Join(configDir, legacyKeyIDName), []byte(kid), 0o600)
	writeCopyTestFile(t, filepath.Join(configDir, runtimeConfigFile), []byte(strings.TrimSpace(`
SERVER_HOSTNAME: registry.example.com:8443
INSTANCE_SERVICE_KEY_SERVICE: quay
`)+"\n"), 0o600)

	db, err := dbcore.OpenSQLite(dbPath)
	require.NoError(t, err)
	defer db.Close()
	_, err = db.ExecContext(t.Context(), `
		INSERT INTO servicekeyapproval (id, approval_type, approved_date, notes)
		VALUES (1, 'automatic', datetime('now'), '')
	`)
	require.NoError(t, err)
	jwk := marshalTestJWK(t, &key.PublicKey, kid)
	_, err = db.ExecContext(t.Context(), `
		INSERT INTO servicekey
			(id, name, kid, service, jwk, metadata, created_date, expiration_date, approval_id)
		VALUES
			(1, 'quay', ?, 'quay', ?, '{}', datetime('now'), datetime('now', '+1 hour'), 1)
	`, kid, jwk)
	require.NoError(t, err)
}

type sourceMaterialRunner struct {
	outputs map[string]string
}

func (r *sourceMaterialRunner) Run(context.Context, string, ...string) error { return nil }

func (r *sourceMaterialRunner) Output(_ context.Context, name string, args ...string) (string, error) {
	if name != "podman" || len(args) != 4 || args[0] != "exec" || args[1] != sourceContainerName || args[2] != "cat" {
		return "", fmt.Errorf("unexpected source material command: %s %v", name, args)
	}
	output, ok := r.outputs[args[3]]
	if !ok {
		return "", fmt.Errorf("no output for %s", args[3])
	}
	return output, nil
}
