package dbcore

import (
	"bytes"
	"path/filepath"
	"strings"
	"testing"
)

func TestSetup_FreshDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := ensureSchema(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if ver != TargetVersion {
		t.Errorf("version = %q, want %q", ver, TargetVersion)
	}
}

func TestSetup_ExistingDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := ensureSchema(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}
	if err := ensureSchema(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}
}

// TestSetup_UpgradesApprovedOMRSourceRevision proves that ensureSchema routes
// a non-current database through the same explicit RunBridge compatibility
// step used by the OMR `quay migrate` path, rather than a separate,
// independently-validated mechanism.
func TestSetup_UpgradesApprovedOMRSourceRevision(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	if _, err := db.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", ApprovedOMRSourceVersion); err != nil {
		t.Fatalf("stamp revision: %v", err)
	}

	if err := ensureSchema(ctx, db, dbPath); err != nil {
		t.Fatalf("ensureSchema: %v", err)
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if ver != TargetVersion {
		t.Errorf("version = %q, want %q", ver, TargetVersion)
	}
}

// TestSetup_RejectsUnsupportedExistingRevision proves that ensureSchema fails
// closed for a database at an existing but unsupported revision instead of
// silently reapplying the compatibility SQL against an unvalidated source.
func TestSetup_RejectsUnsupportedExistingRevision(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	if _, err := db.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", "ffffffffffff"); err != nil {
		t.Fatalf("stamp revision: %v", err)
	}

	err = ensureSchema(ctx, db, dbPath)
	if err == nil || !strings.Contains(err.Error(), "unsupported OMR source revision") {
		t.Fatalf("ensureSchema error = %v, want source rejection", err)
	}
}
