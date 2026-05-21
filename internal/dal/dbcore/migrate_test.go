package dbcore

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestInitDatabase(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	var buf bytes.Buffer
	ctx := context.Background()

	if err := InitDatabase(ctx, db, &buf); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, "tables") {
		t.Errorf("expected summary with table count, got: %s", output)
	}

	// Verify tables were created.
	var tableCount int
	if err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount); err != nil {
		t.Fatalf("count tables: %v", err)
	}

	if tableCount < 100 {
		t.Errorf("expected 100+ tables, got %d", tableCount)
	}

	// Verify alembic_version has a value.
	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if ver == "" {
		t.Error("expected non-empty alembic version after init")
	}
}

func TestInitDatabase_RejectsExisting(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	ctx := context.Background()

	// First init should succeed.
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("first InitDatabase: %v", err)
	}

	// Second init should fail.
	err = InitDatabase(ctx, db, &bytes.Buffer{})
	if err == nil {
		t.Fatal("expected error on second init")
	}
	if !strings.Contains(err.Error(), "already contains") {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestSchemaVersion_EmptyDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "empty.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	ver, err := SchemaVersion(context.Background(), db)
	if err != nil {
		t.Fatalf("SchemaVersion on empty db: %v", err)
	}
	if ver != "" {
		t.Errorf("expected empty version for uninitialised db, got %q", ver)
	}
}

func TestIntegrityCheck(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	ctx := context.Background()
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	if err := IntegrityCheck(ctx, db); err != nil {
		t.Errorf("IntegrityCheck failed: %v", err)
	}
}

func TestBackupAndClean(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")

	// Create the file to back up.
	if err := os.WriteFile(dbPath, []byte("test"), 0o644); err != nil {
		t.Fatalf("write db: %v", err)
	}

	// Create 4 backups with distinct names (timestamps within the same second
	// would collide, so we create them manually).
	var paths []string
	for i := 0; i < 4; i++ {
		p := filepath.Join(dir, fmt.Sprintf("test.db.backup-2026010%dT120000Z", i))
		if err := os.WriteFile(p, []byte("backup"), 0o644); err != nil {
			t.Fatalf("write backup %d: %v", i, err)
		}
		paths = append(paths, p)
	}

	// Clean, keeping 2.
	if err := CleanOldBackups(dbPath, 2); err != nil {
		t.Fatalf("CleanOldBackups: %v", err)
	}

	// Oldest 2 should be gone, newest 2 should remain.
	for _, p := range paths[:2] {
		if _, err := os.Stat(p); !os.IsNotExist(err) {
			t.Errorf("expected %s to be deleted", p)
		}
	}
	for _, p := range paths[2:] {
		if _, err := os.Stat(p); err != nil {
			t.Errorf("expected %s to exist: %v", p, err)
		}
	}
}
