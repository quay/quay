package migrate

import (
	"bytes"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/quay/quay/internal/dal/dbcore"
)

func TestValidateSource_ValidDB(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay_sqlite.db")

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	if err := dbcore.InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "3f8d7acdf7f9"); err != nil {
		t.Fatalf("stamp approved revision: %v", err)
	}
	db.Close()

	certDir := t.TempDir()
	writeSelfSignedCert(t, certDir)
	seedExistingSchemaRegistryKey(t, dbPath, certDir)

	storageDir := t.TempDir()
	os.MkdirAll(filepath.Join(storageDir, "sha256", "ab"), 0o750)

	targetDir := t.TempDir() + "/target"

	m := &Migrator{
		DataDir:     targetDir,
		SkipInstall: true,
		Out:         &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir:   certDir,
			DBPath:      dbPath,
			StoragePath: storageDir,
			Hostname:    "localhost",
		},
	}

	if err := m.validate(t.Context()); err != nil {
		t.Fatalf("validate: %v", err)
	}
}

func TestValidateSource_CorruptDB(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay_sqlite.db")
	os.WriteFile(dbPath, []byte("not a database"), 0o644)

	m := &Migrator{
		DataDir:     t.TempDir() + "/target",
		SkipInstall: true,
		Out:         &bytes.Buffer{},
		Source: OMRSource{
			DBPath: dbPath,
		},
	}

	if err := m.validate(t.Context()); err == nil {
		t.Fatal("expected error for corrupt DB")
	}
}

func TestValidateSource_RequiresHostnameWhenInstalling(t *testing.T) {
	m := validInstallMigrator(t)
	m.Source.Hostname = ""

	err := m.validate(t.Context())
	if err == nil {
		t.Fatal("expected error for missing hostname")
	}
}

func TestValidateSource_RejectsInvalidHostnameWhenInstalling(t *testing.T) {
	m := validInstallMigrator(t)
	m.Source.Hostname = "bad_host"

	err := m.validate(t.Context())
	if err == nil {
		t.Fatal("expected error for invalid hostname")
	}
}

func TestValidateSource_RequiresRegistryJWTContinuityMaterial(t *testing.T) {
	t.Run("config directory", func(t *testing.T) {
		m := validInstallMigrator(t)
		m.Source.ConfigDir = ""

		err := m.validate(t.Context())

		if err == nil || !strings.Contains(err.Error(), "source config directory not detected") {
			t.Fatalf("validate error = %v, want missing source config directory", err)
		}
	})

	t.Run("config file", func(t *testing.T) {
		m := validInstallMigrator(t)
		if err := os.Remove(filepath.Join(m.Source.ConfigDir, runtimeConfigFile)); err != nil {
			t.Fatalf("remove source config: %v", err)
		}

		err := m.validate(t.Context())

		if err == nil || !strings.Contains(err.Error(), "read source config") {
			t.Fatalf("validate error = %v, want missing source config", err)
		}
	})

	t.Run("signing key", func(t *testing.T) {
		m := validInstallMigrator(t)
		if err := os.Remove(filepath.Join(m.Source.ConfigDir, legacyPrivateKeyName)); err != nil {
			t.Fatalf("remove source signing key: %v", err)
		}

		err := m.validateRegistryJWTSource(t.Context())

		if err == nil || !strings.Contains(err.Error(), "registry JWT key validation") {
			t.Fatalf("validateRegistryJWTSource error = %v, want missing signing key", err)
		}
	})
}

func TestMigrateData_UpgradesApprovedSourceAfterStoppingServices(t *testing.T) {
	m := validInstallMigrator(t)
	runner := &recordingRunner{}
	m.Runner = runner
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}

	db, err := dbcore.OpenSQLite(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "3f8d7acdf7f9"); err != nil {
		t.Fatalf("stamp approved revision: %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	if err := m.migrateData(t.Context()); err != nil {
		t.Fatalf("migrateData: %v", err)
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("source services stopped = %v, want %d stops", runner.runCalls, len(omrServiceNames))
	}

	target, err := dbcore.OpenSQLiteReadOnly(filepath.Join(m.DataDir, "quay.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer target.Close()
	revision, err := dbcore.SchemaVersion(t.Context(), target)
	if err != nil {
		t.Fatal(err)
	}
	if revision != dbcore.TargetVersion {
		t.Errorf("target revision = %q, want %q", revision, dbcore.TargetVersion)
	}
}

func TestMigrateData_RejectsExternalSourceBeforeStoppingServices(t *testing.T) {
	m := validInstallMigrator(t)
	runner := &recordingRunner{}
	m.Runner = runner
	m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}

	db, err := dbcore.OpenSQLite(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "0cdd1f27a450"); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	err = m.migrateData(t.Context())
	if err == nil || !strings.Contains(err.Error(), "unsupported OMR source revision") {
		t.Fatalf("migrateData error = %v, want unsupported revision", err)
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("source services were stopped before preflight rejection: %v", runner.runCalls)
	}

	readOnly, err := dbcore.OpenSQLiteReadOnly(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	defer readOnly.Close()
	revision, err := dbcore.SchemaVersion(t.Context(), readOnly)
	if err != nil {
		t.Fatal(err)
	}
	if revision != "0cdd1f27a450" {
		t.Errorf("source revision = %q, want unchanged unsupported revision", revision)
	}
}

func TestMigrateData_RejectsUnsupportedAuthenticationBeforeStoppingServices(t *testing.T) {
	for _, provider := range []string{"LDAP", "JWT", "Keystone", "OIDC", "AppToken", "", "Unknown"} {
		t.Run(provider, func(t *testing.T) {
			m := validInstallMigrator(t)
			runner := &recordingRunner{}
			m.Runner = runner
			m.Source.UnitFiles = []string{"/etc/systemd/system/quay-app.service"}

			configPath := filepath.Join(m.Source.ConfigDir, runtimeConfigFile)
			configData, err := os.ReadFile(configPath)
			if err != nil {
				t.Fatal(err)
			}
			replacement := `AUTHENTICATION_TYPE: "` + provider + `"`
			configData = []byte(strings.Replace(string(configData), "AUTHENTICATION_TYPE: Database", replacement, 1))
			if err := os.WriteFile(configPath, configData, 0o600); err != nil {
				t.Fatal(err)
			}

			err = m.migrateData(t.Context())
			want := "unsupported authentication provider"
			if provider == "" {
				want = "AUTHENTICATION_TYPE must be a non-empty string"
			}
			if err == nil || !strings.Contains(err.Error(), want) {
				t.Fatalf("migrateData error = %v, want %q", err, want)
			}
			if len(runner.runCalls) != 0 {
				t.Fatalf("source services were stopped before auth rejection: %v", runner.runCalls)
			}
		})
	}
}

func TestValidateSource_RejectsMissingAuthenticationType(t *testing.T) {
	m := validInstallMigrator(t)
	configPath := filepath.Join(m.Source.ConfigDir, runtimeConfigFile)
	configData, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	configData = []byte(strings.Replace(string(configData), "AUTHENTICATION_TYPE: Database\n", "", 1))
	if err := os.WriteFile(configPath, configData, 0o600); err != nil {
		t.Fatal(err)
	}

	err = m.validate(t.Context())
	if err == nil || !strings.Contains(err.Error(), "AUTHENTICATION_TYPE is missing") {
		t.Fatalf("validate error = %v, want missing auth type", err)
	}
}

func TestValidateSource_ChecksRobotTokenDecryption(t *testing.T) {
	m := validInstallMigrator(t)
	db, err := dbcore.OpenSQLite(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		`INSERT INTO user (id, username, email, verified, organization, robot, invoice_email, last_invalid_login) VALUES (1, 'owner+robot', 'robot@example.com', 1, 0, 1, 0, datetime('now'))`,
		`INSERT INTO robotaccounttoken (id, robot_account_id, token) VALUES (1, 1, 'v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==')`,
	} {
		if _, err := db.ExecContext(t.Context(), statement); err != nil {
			t.Fatal(err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	db, err = dbcore.OpenSQLiteReadOnly(m.Source.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if err := m.validateSourceAuth(t.Context(), db); err != nil {
		t.Fatalf("validateSourceAuth with decryptable token: %v", err)
	}

	configPath := filepath.Join(m.Source.ConfigDir, runtimeConfigFile)
	configData, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	configData = []byte(strings.Replace(string(configData), "DATABASE_SECRET_KEY: test1234", "DATABASE_SECRET_KEY: wrong-key", 1))
	if err := os.WriteFile(configPath, configData, 0o600); err != nil {
		t.Fatal(err)
	}

	err = m.validateSourceAuth(t.Context(), db)
	if err == nil || !strings.Contains(err.Error(), "robot token cannot be decrypted") {
		t.Fatalf("validateSourceAuth error = %v, want robot token decryption failure", err)
	}
}

func TestValidateTarget_NotEmpty(t *testing.T) {
	targetDir := t.TempDir()
	os.WriteFile(filepath.Join(targetDir, "existing.txt"), []byte("data"), 0o644)

	err := validateTargetDir(targetDir)
	if err == nil {
		t.Fatal("expected error for non-empty target")
	}
}

func TestValidateTarget_MarkerAllowsResume(t *testing.T) {
	targetDir := t.TempDir()
	os.WriteFile(filepath.Join(targetDir, ".migration-in-progress"), []byte(""), 0o644)

	err := validateTargetDir(targetDir)
	if err != nil {
		t.Fatalf("should allow resume with marker: %v", err)
	}
}

func writeSelfSignedCert(t *testing.T, dir string) {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	tmpl := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject:      pkix.Name{CommonName: "test"},
		NotBefore:    time.Now(),
		NotAfter:     time.Now().Add(24 * time.Hour),
	}
	certDER, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})
	keyDER, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		t.Fatal(err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: keyDER})
	os.WriteFile(filepath.Join(dir, "ssl.cert"), certPEM, 0o644)
	os.WriteFile(filepath.Join(dir, "ssl.key"), keyPEM, 0o644)
}

func validInstallMigrator(t *testing.T) *Migrator {
	t.Helper()

	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay_sqlite.db")
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	if err := dbcore.InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "3f8d7acdf7f9"); err != nil {
		t.Fatalf("stamp approved revision: %v", err)
	}
	db.Close()

	certDir := t.TempDir()
	writeSelfSignedCert(t, certDir)
	seedExistingSchemaRegistryKey(t, dbPath, certDir)

	storageDir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(storageDir, "sha256", "ab"), 0o750); err != nil {
		t.Fatalf("create storage dir: %v", err)
	}

	return &Migrator{
		DataDir: t.TempDir() + "/target",
		Out:     &bytes.Buffer{},
		Source: OMRSource{
			ConfigDir:   certDir,
			DBPath:      dbPath,
			StoragePath: storageDir,
			Hostname:    "localhost",
			Image:       "quay.io/quay/quay-mirror:test",
		},
	}
}
