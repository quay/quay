package migrate

import (
	"bytes"
	"crypto/rand"
	"crypto/rsa"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/go-jose/go-jose/v4"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/registry/jwtauth"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestCopyData(t *testing.T) {
	srcDir := t.TempDir()
	dbDir := t.TempDir()
	storageDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	createCopyTestDB(t, dbPath)

	writeCopyTestFile(t, filepath.Join(srcDir, "ssl.cert"), []byte("fake-cert"), 0o644)
	writeCopyTestFile(t, filepath.Join(srcDir, "ssl.key"), []byte("fake-key"), 0o600)

	mkdirCopyTestDir(t, filepath.Join(storageDir, "sha256", "ab"), 0o750)
	writeCopyTestFile(t, filepath.Join(storageDir, "sha256", "ab", "abcdef"), []byte("blob-data"), 0o644)

	targetDir := filepath.Join(t.TempDir(), "target")

	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir:   srcDir,
			DBPath:      dbPath,
			StoragePath: storageDir,
		},
	}

	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("copyData: %v", err)
	}

	if _, err := os.Stat(filepath.Join(targetDir, "quay.db")); err != nil {
		t.Error("quay.db not found in target")
	}
	if _, err := os.Stat(filepath.Join(targetDir, "ssl.cert")); err != nil {
		t.Error("ssl.cert not found in target")
	}
	if _, err := os.Stat(filepath.Join(targetDir, "ssl.key")); err != nil {
		t.Error("ssl.key not found in target")
	}

	blobPath := filepath.Join(targetDir, "storage", "sha256", "ab", "abcdef")
	if _, err := os.Stat(blobPath); err != nil {
		t.Errorf("blob not found: %s", blobPath)
	}

	if _, err := os.Stat(filepath.Join(targetDir, markerFile)); err != nil {
		t.Error("marker file should exist after copy")
	}
}

func TestCopyData_WritesRuntimeConfigWithSourceSecrets(t *testing.T) {
	srcDir := t.TempDir()
	dbDir := t.TempDir()
	storageDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	createCopyTestDB(t, dbPath)
	seedCopyTestRegistryKey(t, dbPath, srcDir)
	writeCopyTestFile(t, filepath.Join(srcDir, "config.yaml"), []byte(`
SERVER_HOSTNAME: old.example.com
PREFERRED_URL_SCHEME: https
DB_URI: sqlite:////old/quay_sqlite.db
DISTRIBUTED_STORAGE_CONFIG:
  old:
    - LocalStorage
    - storage_path: /old/storage
SECRET_KEY: old-secret
DATABASE_SECRET_KEY: old-database-secret
AUTHENTICATION_TYPE: LDAP
ROBOTS_DISALLOW: true
ROBOTS_WHITELIST:
  - init+migratebot
SUPER_USERS:
  - ops-admin
FEATURE_SUPER_USERS: true
FEATURE_SUPERUSERS_FULL_ACCESS: true
FEATURE_USER_LAST_ACCESSED: false
`), 0o600)

	targetDir := filepath.Join(t.TempDir(), "target")
	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir:   srcDir,
			DBPath:      dbPath,
			StoragePath: storageDir,
			Hostname:    "localhost",
		},
	}

	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("copyData: %v", err)
	}

	cfg, err := config.Load(filepath.Join(targetDir, "config.yaml"))
	if err != nil {
		t.Fatalf("load generated runtime config: %v", err)
	}
	if cfg.SecretKey != "old-secret" {
		t.Fatalf("SecretKey = %q, want source secret", cfg.SecretKey)
	}
	if cfg.DatabaseSecretKey != "old-database-secret" {
		t.Fatalf("DatabaseSecretKey = %q, want source database secret", cfg.DatabaseSecretKey)
	}
	if cfg.DBURI != "sqlite:////data/quay.db" {
		t.Fatalf("DBURI = %q, want migrated runtime DB path", cfg.DBURI)
	}
	if cfg.AuthenticationType != "LDAP" {
		t.Fatalf("AuthenticationType = %q, want source authentication type", cfg.AuthenticationType)
	}
	entry := cfg.DistributedStorageConfig["default"]
	if entry.Driver != "LocalStorage" || entry.Params["storage_path"] != "/data/storage" {
		t.Fatalf("storage config = %#v, want LocalStorage at /data/storage", entry)
	}
	if !cfg.RobotsDisallow {
		t.Fatal("RobotsDisallow = false, want source setting preserved")
	}
	if got := cfg.RobotsWhitelist; len(got) != 1 || got[0] != "init+migratebot" {
		t.Fatalf("RobotsWhitelist = %#v, want source whitelist", got)
	}
	if got := cfg.SuperUsers; len(got) != 1 || got[0] != "ops-admin" {
		t.Fatalf("SuperUsers = %#v, want source superusers", got)
	}
	if cfg.FeatureSuperUsers == nil || !*cfg.FeatureSuperUsers {
		t.Fatalf("FeatureSuperUsers = %#v, want source true", cfg.FeatureSuperUsers)
	}
	if cfg.FeatureSuperUsersFullAccess == nil || !*cfg.FeatureSuperUsersFullAccess {
		t.Fatalf("FeatureSuperUsersFullAccess = %#v, want source true", cfg.FeatureSuperUsersFullAccess)
	}
	if cfg.FeatureUserLastAccessed == nil || *cfg.FeatureUserLastAccessed {
		t.Fatalf("FeatureUserLastAccessed = %#v, want source false", cfg.FeatureUserLastAccessed)
	}
	if cfg.ServerHostname != "localhost:8443" {
		t.Fatalf("ServerHostname = %q, want public hostname with port", cfg.ServerHostname)
	}
	if _, err := jwtauth.LoadPrivateKey(filepath.Join(targetDir, jwtauth.KeyFileName)); err != nil {
		t.Fatalf("load imported registry JWT key: %v", err)
	}
}

func TestCopyData_SkipsRuntimeConfigWhenSourceConfigMissing(t *testing.T) {
	srcDir := t.TempDir()
	dbDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	createCopyTestDB(t, dbPath)

	targetDir := filepath.Join(t.TempDir(), "target")
	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir: srcDir,
			DBPath:    dbPath,
		},
	}

	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("copyData: %v", err)
	}
	if _, err := os.Stat(filepath.Join(targetDir, "quay.db")); err != nil {
		t.Fatalf("quay.db not found in target: %v", err)
	}
	if _, err := os.Stat(filepath.Join(targetDir, runtimeConfigFile)); !os.IsNotExist(err) {
		t.Fatalf("runtime config stat err = %v, want not exist", err)
	}
}

func TestWriteRuntimeConfigPreservesSourcePort(t *testing.T) {
	configDir := t.TempDir()
	writeCopyTestFile(t, filepath.Join(configDir, runtimeConfigFile), []byte("SERVER_HOSTNAME: old.example.com:9443\n"), 0o600)
	targetDir := t.TempDir()
	migrator := &Migrator{
		DataDir: targetDir,
		Source: OMRSource{
			ConfigDir: configDir,
			Hostname:  "registry.example.com",
		},
	}
	sourceCfg := config.NewDefault("old.example.com:9443", "/old/storage")

	require.NoError(t, migrator.writeRuntimeConfig(sourceCfg))
	runtimeCfg, err := config.Load(filepath.Join(targetDir, runtimeConfigFile))
	require.NoError(t, err)
	assert.Equal(t, "registry.example.com:9443", runtimeCfg.ServerHostname)
}

func TestWriteRuntimeConfigDefaultsPortForBareSourceHostname(t *testing.T) {
	tests := []struct {
		name, sourceHostname string
	}{
		{name: "DNS", sourceHostname: "old.example.com"},
		{name: "IPv4", sourceHostname: "192.0.2.1"},
		{name: "IPv6", sourceHostname: "2001:db8::1"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			configDir := t.TempDir()
			writeCopyTestFile(t, filepath.Join(configDir, runtimeConfigFile), []byte("SERVER_HOSTNAME: old.example.com\n"), 0o600)
			targetDir := t.TempDir()
			migrator := &Migrator{
				DataDir: targetDir,
				Source:  OMRSource{ConfigDir: configDir, Hostname: "registry.example.com"},
			}

			err := migrator.writeRuntimeConfig(config.NewDefault(tt.sourceHostname, "/old/storage"))

			require.NoError(t, err)
			runtimeCfg, err := config.Load(filepath.Join(targetDir, runtimeConfigFile))
			require.NoError(t, err)
			assert.Equal(t, "registry.example.com:8443", runtimeCfg.ServerHostname)
		})
	}
}

func TestWriteRuntimeConfigRejectsMalformedSourceHostname(t *testing.T) {
	configDir := t.TempDir()
	writeCopyTestFile(t, filepath.Join(configDir, runtimeConfigFile), []byte("SERVER_HOSTNAME: old.example.com\n"), 0o600)
	targetDir := t.TempDir()
	migrator := &Migrator{
		DataDir: targetDir,
		Source:  OMRSource{ConfigDir: configDir, Hostname: "registry.example.com"},
	}

	err := migrator.writeRuntimeConfig(config.NewDefault("old.example.com:9443:extra", "/old/storage"))

	require.ErrorContains(t, err, "parse runtime SERVER_HOSTNAME")
	_, statErr := os.Stat(filepath.Join(targetDir, runtimeConfigFile))
	assert.ErrorIs(t, statErr, os.ErrNotExist)
}

func TestCopyData_Idempotent(t *testing.T) {
	srcDir := t.TempDir()
	dbDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	createCopyTestDB(t, dbPath)
	writeCopyTestFile(t, filepath.Join(srcDir, "ssl.cert"), []byte("cert"), 0o644)
	writeCopyTestFile(t, filepath.Join(srcDir, "ssl.key"), []byte("key"), 0o600)

	targetDir := filepath.Join(t.TempDir(), "target")

	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir: srcDir,
			DBPath:    dbPath,
		},
	}

	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("first copy: %v", err)
	}
	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("second copy (idempotent): %v", err)
	}
}

func TestCopyData_RecopiesDatabaseWhenMarkerExists(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "quay_sqlite.db")
	createCopyTestDB(t, dbPath)

	targetDir := filepath.Join(t.TempDir(), "target")
	mkdirCopyTestDir(t, targetDir, 0o750)
	writeCopyTestFile(t, filepath.Join(targetDir, markerFile), []byte("migration in progress\n"), 0o600)

	sourceBytes, err := os.ReadFile(dbPath) //nolint:gosec // test fixture path is under t.TempDir.
	if err != nil {
		t.Fatalf("read source db: %v", err)
	}
	writeCopyTestFile(t, filepath.Join(targetDir, "quay.db"), bytes.Repeat([]byte("x"), len(sourceBytes)), 0o600)

	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			DBPath: dbPath,
		},
	}

	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("copyData: %v", err)
	}

	targetBytes, err := os.ReadFile(filepath.Join(targetDir, "quay.db")) //nolint:gosec // test fixture path is under t.TempDir.
	if err != nil {
		t.Fatalf("read target db: %v", err)
	}
	if !bytes.Equal(targetBytes, sourceBytes) {
		t.Fatal("target database was not recopied when migration marker existed")
	}
}

func TestCopyData_CheckpointsSourceWAL(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "quay_sqlite.db")
	srcDB, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite source: %v", err)
	}
	defer func() { _ = srcDB.Close() }()

	if _, err := srcDB.ExecContext(t.Context(), "PRAGMA journal_mode=WAL"); err != nil {
		t.Fatalf("enable WAL: %v", err)
	}
	if _, err := srcDB.ExecContext(t.Context(), "CREATE TABLE wal_test (value TEXT)"); err != nil {
		t.Fatalf("create table: %v", err)
	}
	if _, err := srcDB.ExecContext(t.Context(), "INSERT INTO wal_test (value) VALUES ('committed-in-wal')"); err != nil {
		t.Fatalf("insert row: %v", err)
	}

	targetDir := filepath.Join(t.TempDir(), "target")
	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			DBPath: dbPath,
		},
	}

	if err := m.copyData(t.Context()); err != nil {
		t.Fatalf("copyData: %v", err)
	}

	targetDB, err := dbcore.OpenSQLite(filepath.Join(targetDir, "quay.db"))
	if err != nil {
		t.Fatalf("open target: %v", err)
	}
	defer func() { _ = targetDB.Close() }()

	var value string
	if err := targetDB.QueryRowContext(t.Context(), "SELECT value FROM wal_test").Scan(&value); err != nil {
		t.Fatalf("query copied row: %v", err)
	}
	if value != "committed-in-wal" {
		t.Errorf("copied value = %q, want committed-in-wal", value)
	}
}

func createCopyTestDB(t *testing.T, dbPath string) {
	t.Helper()
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer func() { _ = db.Close() }()

	if _, err := db.ExecContext(t.Context(), "CREATE TABLE copy_test (value TEXT)"); err != nil {
		t.Fatalf("create table: %v", err)
	}
	if _, err := db.ExecContext(t.Context(), "INSERT INTO copy_test (value) VALUES ('ok')"); err != nil {
		t.Fatalf("insert row: %v", err)
	}
}

func seedCopyTestRegistryKey(t *testing.T, dbPath, configDir string) *rsa.PrivateKey {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("generate RSA key: %v", err)
	}
	kid, err := jwtauth.KeyID(&key.PublicKey)
	if err != nil {
		t.Fatalf("key ID: %v", err)
	}
	if err := jwtauth.WritePrivateKey(filepath.Join(configDir, legacyPrivateKeyName), key); err != nil {
		t.Fatalf("write legacy private key: %v", err)
	}
	writeCopyTestFile(t, filepath.Join(configDir, legacyKeyIDName), []byte(kid), 0o600)

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("open fixture DB: %v", err)
	}
	defer func() { _ = db.Close() }()
	for _, statement := range []string{
		`CREATE TABLE servicekeyapproval (id INTEGER PRIMARY KEY, approval_type TEXT NOT NULL)`,
		`CREATE TABLE servicekey (id INTEGER PRIMARY KEY, kid TEXT NOT NULL, service TEXT NOT NULL, jwk TEXT NOT NULL, expiration_date DATETIME, approval_id INTEGER)`,
		`INSERT INTO servicekeyapproval (id, approval_type) VALUES (1, 'automatic')`,
	} {
		if _, err := db.ExecContext(t.Context(), statement); err != nil {
			t.Fatalf("seed service key schema: %v", err)
		}
	}
	jwkBytes, err := json.Marshal(jose.JSONWebKey{
		Key: &key.PublicKey, KeyID: kid, Algorithm: string(jose.RS256), Use: "sig",
	})
	if err != nil {
		t.Fatalf("marshal public JWK: %v", err)
	}
	if _, err := db.ExecContext(t.Context(), `
		INSERT INTO servicekey (id, kid, service, jwk, expiration_date, approval_id)
		VALUES (1, ?, 'quay', ?, datetime('now', '+1 hour'), 1)
	`, kid, string(jwkBytes)); err != nil {
		t.Fatalf("seed service key: %v", err)
	}
	return key
}

func TestCopyData_CopiesRootCA(t *testing.T) {
	root := t.TempDir()
	configDir := filepath.Join(root, "quay-config")
	caDir := filepath.Join(root, "quay-rootCA")
	dbDir := t.TempDir()

	mkdirCopyTestDir(t, configDir, 0o750)
	mkdirCopyTestDir(t, caDir, 0o750)

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	createCopyTestDB(t, dbPath)

	writeCopyTestFile(t, filepath.Join(configDir, "ssl.cert"), []byte("fake-cert"), 0o644)
	writeCopyTestFile(t, filepath.Join(configDir, "ssl.key"), []byte("fake-key"), 0o600)
	writeCopyTestFile(t, filepath.Join(caDir, "rootCA.pem"), []byte("fake-root-ca"), 0o644)

	targetDir := filepath.Join(t.TempDir(), "target")
	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir: configDir,
			DBPath:    dbPath,
			RootCADir: caDir,
		},
	}

	require.NoError(t, m.copyData(t.Context()))

	data, err := os.ReadFile(filepath.Join(targetDir, "rootCA.pem"))
	require.NoError(t, err)
	assert.Equal(t, "fake-root-ca", string(data))
}

func TestCopyData_SkipsRootCAWhenNotDetected(t *testing.T) {
	configDir := t.TempDir()
	dbDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	createCopyTestDB(t, dbPath)

	writeCopyTestFile(t, filepath.Join(configDir, "ssl.cert"), []byte("fake-cert"), 0o644)
	writeCopyTestFile(t, filepath.Join(configDir, "ssl.key"), []byte("fake-key"), 0o600)

	targetDir := filepath.Join(t.TempDir(), "target")
	m := &Migrator{
		DataDir: targetDir,
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir: configDir,
			DBPath:    dbPath,
		},
	}

	require.NoError(t, m.copyData(t.Context()))

	_, err := os.Stat(filepath.Join(targetDir, "rootCA.pem"))
	assert.ErrorIs(t, err, os.ErrNotExist)
}

func mkdirCopyTestDir(t *testing.T, path string, perm os.FileMode) {
	t.Helper()
	if err := os.MkdirAll(path, perm); err != nil {
		t.Fatalf("mkdir fixture %s: %v", path, err)
	}
}

func writeCopyTestFile(t *testing.T, path string, data []byte, perm os.FileMode) {
	t.Helper()
	if err := os.WriteFile(path, data, perm); err != nil {
		t.Fatalf("write fixture %s: %v", path, err)
	}
}
