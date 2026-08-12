package dbcore

import (
	"bytes"
	"database/sql"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"testing"
)

func TestOpenSQLiteReadOnly(t *testing.T) {
	t.Run("does not create a missing database", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "missing.db")
		if _, err := OpenSQLiteReadOnly(path); err == nil {
			t.Fatal("OpenSQLiteReadOnly succeeded for missing database")
		}
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("missing database was created: %v", err)
		}
	})

	t.Run("rejects writes", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "source.db")
		db, err := OpenSQLite(path)
		if err != nil {
			t.Fatal(err)
		}
		if err := InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
			t.Fatal(err)
		}
		if err := db.Close(); err != nil {
			t.Fatal(err)
		}

		readOnly, err := OpenSQLiteReadOnly(path)
		if err != nil {
			t.Fatal(err)
		}
		defer readOnly.Close()
		if _, err := readOnly.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = 'changed'"); err == nil {
			t.Fatal("write through read-only database succeeded")
		}
	})

	t.Run("opens relative paths", func(t *testing.T) {
		dir := t.TempDir()
		createMarkerDatabase(t, filepath.Join(dir, "relative.db"), "relative")
		t.Chdir(dir)

		readOnly, err := OpenSQLiteReadOnly("relative.db")
		if err != nil {
			t.Fatal(err)
		}
		defer readOnly.Close()

		var marker string
		if err := readOnly.QueryRowContext(t.Context(), "SELECT marker FROM source_marker").Scan(&marker); err != nil {
			t.Fatal(err)
		}
		if marker != "relative" {
			t.Fatalf("opened marker %q, want relative database", marker)
		}
	})

	t.Run("opens paths containing URI delimiters", func(t *testing.T) {
		dir := t.TempDir()
		sourcePath := filepath.Join(dir, "source?with#symbols&.db")
		siblingPath := filepath.Join(dir, "source")

		createMarkerDatabase(t, sourcePath, "source")
		createMarkerDatabase(t, siblingPath, "sibling")

		readOnly, err := OpenSQLiteReadOnly(sourcePath)
		if err != nil {
			t.Fatal(err)
		}
		defer readOnly.Close()

		var marker string
		if err := readOnly.QueryRowContext(t.Context(), "SELECT marker FROM source_marker").Scan(&marker); err != nil {
			t.Fatal(err)
		}
		if marker != "source" {
			t.Fatalf("opened marker %q, want source database", marker)
		}
		if _, err := readOnly.ExecContext(t.Context(), "UPDATE source_marker SET marker = 'changed'"); err == nil {
			t.Fatal("write through delimiter path succeeded")
		}
	})
}

func TestOpenSQLiteReadOnly_SucceedsWithReadOnlyDirectory(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "source.db")

	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "CREATE TABLE ro_test (v TEXT)"); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "INSERT INTO ro_test (v) VALUES ('hello')"); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	if err := os.Chmod(dir, 0o555); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(dir, 0o755) })

	readOnly, err := OpenSQLiteReadOnly(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLiteReadOnly should succeed on read-only directory: %v", err)
	}
	defer readOnly.Close()

	var v string
	if err := readOnly.QueryRowContext(t.Context(), "SELECT v FROM ro_test").Scan(&v); err != nil {
		t.Fatalf("SELECT failed: %v", err)
	}
	if v != "hello" {
		t.Fatalf("got %q, want hello", v)
	}

	walPath := dbPath + "-wal"
	shmPath := dbPath + "-shm"
	if _, err := os.Stat(walPath); err == nil {
		t.Fatalf("WAL file should not be created in read-only directory: %s", walPath)
	}
	if _, err := os.Stat(shmPath); err == nil {
		t.Fatalf("SHM file should not be created in read-only directory: %s", shmPath)
	}
}

func TestOpenSQLite_PathsContainingURIDelimiters(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "omr?with#symbols&.db")

	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	if err := InitDatabase(t.Context(), db, io.Discard); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	if _, err := os.Stat(dbPath); err != nil {
		t.Fatalf("expected database created at literal path %q: %v", dbPath, err)
	}
}

func createMarkerDatabase(t *testing.T, path, marker string) {
	t.Helper()
	uri := url.URL{Scheme: sqliteURIScheme, Path: path}
	db, err := sql.Open("sqlite", uri.String())
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if _, err := db.ExecContext(t.Context(), "CREATE TABLE source_marker (marker TEXT NOT NULL)"); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(t.Context(), "INSERT INTO source_marker (marker) VALUES (?)", marker); err != nil {
		t.Fatal(err)
	}
}
