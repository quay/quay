package dbcore

import (
	"bytes"
	"path/filepath"
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

func TestSetup_ExistingBridgeTargetDB(t *testing.T) {
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
	if _, err := db.ExecContext(ctx, `DROP INDEX tag_repository_id_name_active`); err != nil {
		t.Fatalf("drop active index: %v", err)
	}
	if _, err := db.ExecContext(ctx, `DROP INDEX tag_repository_id_name_lifetime_end_ms`); err != nil {
		t.Fatalf("drop history index: %v", err)
	}
	if _, err := db.ExecContext(ctx,
		`CREATE UNIQUE INDEX tag_repository_id_name_lifetime_end_ms ON tag (repository_id, name, lifetime_end_ms)`,
	); err != nil {
		t.Fatalf("create old unique history index: %v", err)
	}
	if _, err := db.ExecContext(ctx, `UPDATE alembic_version SET version_num = ?`, BridgeTargetVersion); err != nil {
		t.Fatalf("stamp bridge version: %v", err)
	}

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
	assertTagIndexes(t, db)
}
