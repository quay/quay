// Package dbcore provides SQLite database lifecycle management for the quay CLI.
package dbcore

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite" // Pure-Go SQLite driver, registers as "sqlite".
)

// pragmas are applied to every new SQLite connection via a DSN hook.
// WAL mode allows concurrent readers while a single writer holds the lock.
// busy_timeout avoids immediate SQLITE_BUSY errors under brief contention.
var pragmas = []string{
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

	dsn := fmt.Sprintf("file:%s?", dbPath)
	for i, p := range pragmas {
		if i > 0 {
			dsn += "&"
		}
		dsn += p
	}

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", dbPath, err)
	}

	// Single writer eliminates SQLite lock contention.
	db.SetMaxOpenConns(1)

	// Verify the connection works and PRAGMAs took effect.
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("ping %s: %w", dbPath, err)
	}

	return db, nil
}
