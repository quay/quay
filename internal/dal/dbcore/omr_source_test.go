package dbcore

import (
	"bytes"
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

	// The copier replaces the lookup seeds with source-owned IDs.
	for _, table := range []string{"visibility", "repositorykind", "mediatype", "tagkind"} {
		var n int
		if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM "+table).Scan(&n); err != nil {
			t.Fatalf("count %s: %v", table, err)
		}
		if n == 0 {
			t.Errorf("expected %s to be seeded, found 0 rows", table)
		}
	}

	// Alembic creates eight locations; Quay creates "default" at runtime.
	var storageLocationCount, runtimeDefaultCount int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM imagestoragelocation").Scan(&storageLocationCount); err != nil {
		t.Fatalf("count imagestoragelocation: %v", err)
	}
	if storageLocationCount != 8 {
		t.Errorf("imagestoragelocation count = %d, want 8 Alembic seed rows", storageLocationCount)
	}
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM imagestoragelocation WHERE name = 'default'").Scan(&runtimeDefaultCount); err != nil {
		t.Fatalf("count runtime default storage locations: %v", err)
	}
	if runtimeDefaultCount != 0 {
		t.Errorf("expected no runtime-created default storage location, found %d", runtimeDefaultCount)
	}

	// Data tables start empty until the PostgreSQL copy.
	const tagTable = "tag"
	for _, table := range []string{"user", "repository", manifestTable, tagTable} {
		var n int
		if err := db.QueryRowContext(t.Context(), `SELECT count(*) FROM "`+table+`"`).Scan(&n); err != nil {
			t.Fatalf("count %s: %v", table, err)
		}
		if n != 0 {
			t.Errorf("expected %s to start empty, found %d rows", table, n)
		}
	}

	if err := InitOMRSourceIntermediate(t.Context(), db, &out); err == nil {
		t.Fatal("expected second InitOMRSourceIntermediate call to fail on an already-populated database")
	}
}
