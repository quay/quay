// Package dbcore provides SQLite database lifecycle management for the quay CLI.
package dbcore

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite" // Pure-Go SQLite driver, registers as "sqlite".
)

// pragmas are applied to every new SQLite connection via a DSN hook.
// WAL mode allows concurrent readers while a single writer holds the lock.
// busy_timeout avoids immediate SQLITE_BUSY errors under brief contention.
var pragmas = []string{
	"foreign_keys(1)",
	"journal_mode(WAL)",
	"busy_timeout(10000)",
	"synchronous(NORMAL)",
	"wal_autocheckpoint(1000)",
}

// OpenSQLite opens (or creates) the SQLite database at dbPath and configures
// PRAGMAs via DSN parameters. Write transactions acquire the SQLite writer lock
// when they begin, before they can establish a stale WAL snapshot. The returned
// *sql.DB has MaxOpenConns=1 to serialize writes within each database handle.
func OpenSQLite(dbPath string) (*sql.DB, error) {
	// Ensure parent directory exists.
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return nil, fmt.Errorf("create database directory %s: %w", dir, err)
	}

	query := make(url.Values)
	query.Set("_txlock", "immediate")
	for _, p := range pragmas {
		query.Add("_pragma", p)
	}
	dsn := (&url.URL{
		Scheme:   "file",
		OmitHost: true,
		Path:     dbPath,
		RawQuery: query.Encode(),
	}).String()

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", dbPath, err)
	}

	// A single connection serializes writes within this database handle.
	db.SetMaxOpenConns(1)

	// Verify the connection works and PRAGMAs took effect.
	if err := db.PingContext(context.Background()); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping %s: %w", dbPath, err)
	}

	return db, nil
}
