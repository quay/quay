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
	db.Close()

	certDir := t.TempDir()
	writeSelfSignedCert(t, certDir)

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
	db.Close()

	certDir := t.TempDir()
	writeSelfSignedCert(t, certDir)

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
