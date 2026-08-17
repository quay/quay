package dbcore

import (
	"bytes"
	"database/sql"
	"fmt"
	"path/filepath"
	"testing"
)

func TestInitOMRSourceIntermediate(t *testing.T) {
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "omr-source.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	var out bytes.Buffer
	if err := InitOMRSourceIntermediate(t.Context(), db, &out); err != nil {
		t.Fatalf("InitOMRSourceIntermediate: %v", err)
	}

	ver, err := SchemaVersion(t.Context(), db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if ver != ApprovedOMRSourceVersion {
		t.Fatalf("alembic_version = %q, want %q", ver, ApprovedOMRSourceVersion)
	}

	if err := IntegrityCheck(t.Context(), db); err != nil {
		t.Errorf("IntegrityCheck: %v", err)
	}
	if err := foreignKeyCheck(t.Context(), db); err != nil {
		t.Errorf("foreign key check: %v", err)
	}

	for _, table := range emptyIntermediateTables(t, db) {
		var count int
		if err := db.QueryRowContext(t.Context(), fmt.Sprintf("SELECT count(*) FROM %q", table)).Scan(&count); err != nil {
			t.Fatalf("count %s: %v", table, err)
		}
		if count != 0 {
			t.Errorf("expected %s to start empty, found %d rows", table, count)
		}
	}

	if err := InitOMRSourceIntermediate(t.Context(), db, &out); err == nil {
		t.Fatal("expected second InitOMRSourceIntermediate call to fail on an already-populated database")
	}
}

func emptyIntermediateTables(t *testing.T, db *sql.DB) []string {
	t.Helper()
	rows, err := db.QueryContext(t.Context(), `SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'`)
	if err != nil {
		t.Fatalf("list intermediate tables: %v", err)
	}
	defer func() { _ = rows.Close() }()

	var tables []string
	for rows.Next() {
		var table string
		if err := rows.Scan(&table); err != nil {
			t.Fatalf("scan intermediate table: %v", err)
		}
		tables = append(tables, table)
	}
	if err := rows.Err(); err != nil {
		t.Fatalf("iterate intermediate tables: %v", err)
	}
	return tables
}
