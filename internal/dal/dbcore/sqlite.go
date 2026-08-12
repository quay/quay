// Package dbcore provides SQLite database lifecycle management for the quay CLI.
package dbcore

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	_ "modernc.org/sqlite" // Pure-Go SQLite driver, registers as "sqlite".
)

// sqliteURIScheme is the URI scheme used to build SQLite DSNs.
const sqliteURIScheme = "file"

// dsnParams are applied to every new SQLite connection via a DSN hook.
// WAL mode allows concurrent readers while a single writer holds the lock.
// busy_timeout avoids immediate SQLITE_BUSY errors under brief contention.
var dsnParams = []string{
	"_pragma=foreign_keys(1)",
	"_pragma=journal_mode(WAL)",
	"_pragma=busy_timeout(10000)",
	"_pragma=synchronous(NORMAL)",
	"_pragma=wal_autocheckpoint(1000)",
}

// OpenSQLite opens (or creates) the SQLite database at dbPath and configures
// PRAGMAs via DSN parameters. The returned *sql.DB has MaxOpenConns=1 to
// serialize all writes through a single connection, eliminating lock contention.
func OpenSQLite(dbPath string) (*sql.DB, error) {
	// Ensure parent directory exists.
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return nil, fmt.Errorf("create database directory %s: %w", dir, err)
	}

	// Encode dbPath into the URI so paths containing characters such as
	// '?', '#', or '&' aren't misparsed as the start of the query string.
	uri := url.URL{Scheme: sqliteURIScheme, Path: dbPath, RawQuery: strings.Join(dsnParams, "&"), OmitHost: true}

	db, err := sql.Open("sqlite", uri.String())
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", dbPath, err)
	}

	// Single writer eliminates SQLite lock contention.
	db.SetMaxOpenConns(1)

	// Verify the connection works and PRAGMAs took effect.
	if err := db.PingContext(context.Background()); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping %s: %w", dbPath, err)
	}

	return db, nil
}

// OpenSQLiteReadOnly opens an existing SQLite database for source preflight.
// mode=ro prevents schema or data changes and never creates a missing source.
func OpenSQLiteReadOnly(dbPath string) (*sql.DB, error) {
	if _, err := os.Stat(dbPath); err != nil {
		return nil, fmt.Errorf("source database not found: %s: %w", dbPath, err)
	}

	uri := url.URL{Scheme: sqliteURIScheme, Path: dbPath, RawQuery: "mode=ro&immutable=1", OmitHost: true}
	db, err := sql.Open("sqlite", uri.String())
	if err != nil {
		return nil, fmt.Errorf("open %s read-only: %w", dbPath, err)
	}
	if err := db.PingContext(context.Background()); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping %s read-only: %w", dbPath, err)
	}
	return db, nil
}
