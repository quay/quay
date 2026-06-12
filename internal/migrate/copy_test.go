package migrate

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestCopyData(t *testing.T) {
	srcDir := t.TempDir()
	dbDir := t.TempDir()
	storageDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	os.WriteFile(dbPath, []byte("fake-db-content"), 0o644)

	os.WriteFile(filepath.Join(srcDir, "ssl.cert"), []byte("fake-cert"), 0o644)
	os.WriteFile(filepath.Join(srcDir, "ssl.key"), []byte("fake-key"), 0o600)

	os.MkdirAll(filepath.Join(storageDir, "docker", "registry", "v2", "blobs"), 0o750)
	os.WriteFile(filepath.Join(storageDir, "docker", "registry", "v2", "blobs", "sha256-abc"), []byte("blob-data"), 0o644)

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

	blobPath := filepath.Join(targetDir, "storage", "docker", "registry", "v2", "blobs", "sha256-abc")
	if _, err := os.Stat(blobPath); err != nil {
		t.Errorf("blob not found: %s", blobPath)
	}

	if _, err := os.Stat(filepath.Join(targetDir, markerFile)); err != nil {
		t.Error("marker file should exist after copy")
	}
}

func TestCopyData_Idempotent(t *testing.T) {
	srcDir := t.TempDir()
	dbDir := t.TempDir()

	dbPath := filepath.Join(dbDir, "quay_sqlite.db")
	os.WriteFile(dbPath, []byte("db-data"), 0o644)
	os.WriteFile(filepath.Join(srcDir, "ssl.cert"), []byte("cert"), 0o644)
	os.WriteFile(filepath.Join(srcDir, "ssl.key"), []byte("key"), 0o600)

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
