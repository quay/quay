package dbcore

import (
	"path/filepath"
	"testing"
)

func TestBootstrap_FreshDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := Bootstrap(ctx, db, dbPath); err != nil {
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

func TestBootstrap_ExistingDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := Bootstrap(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}
	if err := Bootstrap(ctx, db, dbPath); err != nil {
		t.Fatal(err)
	}
}
