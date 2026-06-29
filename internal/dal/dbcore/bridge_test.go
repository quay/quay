package dbcore

import (
	"bytes"
	"database/sql"
	"fmt"
	"path/filepath"
	"strings"
	"testing"
)

func TestEnsureColumn_AddsMissing(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback() }()

	if _, err := tx.ExecContext(ctx, "CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, name TEXT)"); err != nil {
		t.Fatal(err)
	}

	if err := ensureColumn(ctx, tx, "test_tbl", "age", "INTEGER DEFAULT 0"); err != nil {
		t.Fatalf("ensureColumn: %v", err)
	}

	// Verify column exists.
	var count int
	err = tx.QueryRowContext(ctx,
		"SELECT count(*) FROM pragma_table_info('test_tbl') WHERE name='age'",
	).Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Error("expected age column to exist")
	}
}

func TestEnsureColumn_SkipsExisting(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback() }()

	if _, err := tx.ExecContext(ctx, "CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, name TEXT)"); err != nil {
		t.Fatal(err)
	}

	// Should not error when column already exists.
	if err := ensureColumn(ctx, tx, "test_tbl", "name", "TEXT"); err != nil {
		t.Fatalf("ensureColumn on existing column: %v", err)
	}
}

func TestEnsureNonUniqueIndex_FixesUnique(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback() }()

	if _, err := tx.ExecContext(ctx, "CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, ns_id INTEGER)"); err != nil {
		t.Fatal(err)
	}
	if _, err := tx.ExecContext(ctx, "CREATE UNIQUE INDEX test_idx ON test_tbl (ns_id)"); err != nil {
		t.Fatal(err)
	}

	if err := ensureNonUniqueIndex(ctx, tx, "test_tbl", "test_idx", "ns_id"); err != nil {
		t.Fatalf("ensureNonUniqueIndex: %v", err)
	}

	// Verify index is now non-unique.
	var indexSQL string
	err = tx.QueryRowContext(ctx,
		"SELECT sql FROM sqlite_master WHERE type='index' AND name='test_idx'",
	).Scan(&indexSQL)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(strings.ToUpper(indexSQL), "UNIQUE") {
		t.Errorf("expected non-unique index, got: %s", indexSQL)
	}
}

func TestEnsureNonUniqueIndex_CreatesWhenMissing(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback() }()

	if _, err := tx.ExecContext(ctx, "CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, ns_id INTEGER)"); err != nil {
		t.Fatal(err)
	}

	if err := ensureNonUniqueIndex(ctx, tx, "test_tbl", "test_idx", "ns_id"); err != nil {
		t.Fatalf("ensureNonUniqueIndex: %v", err)
	}

	// Verify index was created.
	var count int
	err = tx.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='index' AND name='test_idx'",
	).Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Error("expected index to be created")
	}
}

func TestEnsureNonUniqueIndex_SkipsCorrect(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = tx.Rollback() }()

	if _, err := tx.ExecContext(ctx, "CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, ns_id INTEGER)"); err != nil {
		t.Fatal(err)
	}
	if _, err := tx.ExecContext(ctx, "CREATE INDEX test_idx ON test_tbl (ns_id)"); err != nil {
		t.Fatal(err)
	}

	// Should be a no-op.
	if err := ensureNonUniqueIndex(ctx, tx, "test_tbl", "test_idx", "ns_id"); err != nil {
		t.Fatalf("ensureNonUniqueIndex on correct index: %v", err)
	}
}

func TestRunBridge_AlreadyCurrent(t *testing.T) {
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

	var buf bytes.Buffer
	if err := RunBridge(ctx, db, &buf); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}

	if !strings.Contains(buf.String(), "current") {
		t.Errorf("expected 'current' in output, got: %s", buf.String())
	}
}

func TestRunBridge_RejectsUnknownVersion(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	if _, err := db.ExecContext(ctx, "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, "INSERT INTO alembic_version (version_num) VALUES ('unknown_ver_123')"); err != nil {
		t.Fatal(err)
	}

	err := RunBridge(ctx, db, &bytes.Buffer{})
	if err == nil {
		t.Fatal("expected error for unknown version")
	}
	if !strings.Contains(err.Error(), "unknown schema version") {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestRunBridge_CreatesBridgeTables(t *testing.T) {
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

	for _, table := range []string{
		"tagpullstatistics",
		"manifestpullstatistics",
		"orgmirrorconfig",
		"orgmirrorrepository",
		"namespaceimmutabilitypolicy",
		"repositoryimmutabilitypolicy",
		"organizationcontactemail",
	} {
		if _, err := db.ExecContext(ctx, "DROP TABLE "+table); err != nil {
			t.Fatalf("drop %s: %v", table, err)
		}
	}
	if _, err := db.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", "3f8d7acdf7f9"); err != nil {
		t.Fatalf("stamp old version: %v", err)
	}

	if err := RunBridge(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if ver != TargetVersion {
		t.Errorf("version = %q, want %q", ver, TargetVersion)
	}

	for _, table := range []string{
		"tagpullstatistics",
		"manifestpullstatistics",
		"orgmirrorconfig",
		"orgmirrorrepository",
		"namespaceimmutabilitypolicy",
		"repositoryimmutabilitypolicy",
		"organizationcontactemail",
	} {
		var count int
		err := db.QueryRowContext(ctx,
			"SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", table,
		).Scan(&count)
		if err != nil {
			t.Fatalf("query table %s: %v", table, err)
		}
		if count != 1 {
			t.Errorf("expected table %s to exist", table)
		}
	}
}

func openTestDB(t *testing.T) *sql.DB {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), fmt.Sprintf("test-%s.db", t.Name()))
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	return db
}
