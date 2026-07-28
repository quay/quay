package dbcore

import (
	"bytes"
	"database/sql"
	"path/filepath"
	"strings"
	"testing"
)

func TestValidateSourceCompatibilityRejectsAllRevisions(t *testing.T) {
	for _, revision := range []string{TargetVersion, "3f8d7acdf7f9", "0cdd1f27a450", "ffffffffffff"} {
		t.Run(revision, func(t *testing.T) {
			db := openCompatibilityTestDB(t)
			defer db.Close()

			if err := InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
				t.Fatalf("InitDatabase: %v", err)
			}
			if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", revision); err != nil {
				t.Fatalf("stamp revision: %v", err)
			}

			err := ValidateSourceCompatibility(t.Context(), db)
			if err == nil || !strings.Contains(err.Error(), "no OMR source revisions are enabled") {
				t.Fatalf("ValidateSourceCompatibility error = %v, want source rejection", err)
			}
		})
	}
}

func openCompatibilityTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	return db
}

func TestValidateSourceCompatibilityRejectsAmbiguousRevision(t *testing.T) {
	db := openCompatibilityTestDB(t)
	defer db.Close()

	if _, err := db.ExecContext(t.Context(), "CREATE TABLE alembic_version (version_num TEXT NOT NULL)"); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "INSERT INTO alembic_version VALUES (?), (?)", "3f8d7acdf7f9", TargetVersion); err != nil {
		t.Fatal(err)
	}

	err := ValidateSourceCompatibility(t.Context(), db)
	if err == nil || !strings.Contains(err.Error(), "exactly one revision") {
		t.Fatalf("ValidateSourceCompatibility error = %v, want ambiguous revision rejection", err)
	}
}
