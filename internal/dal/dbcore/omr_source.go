package dbcore

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"

	"github.com/quay/quay/internal/dal/schema"
)

// InitOMRSourceIntermediate creates the approved OMR v2 SQLite baseline
// consumed by the PostgreSQL copier and RunBridge.
func InitOMRSourceIntermediate(ctx context.Context, db *sql.DB) error {
	var tableCount int
	err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount)
	if err != nil {
		return fmt.Errorf("check existing tables: %w", err)
	}
	if tableCount > 0 {
		return fmt.Errorf("intermediate database already contains %d tables; refusing to overwrite", tableCount)
	}

	// SQLite ignores this PRAGMA inside a transaction.
	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = OFF"); err != nil {
		return fmt.Errorf("disable foreign keys: %w", err)
	}

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }() //nolint:errcheck // no-op after commit

	if _, err := tx.ExecContext(ctx, schema.OMRSourceSchemaSQL); err != nil {
		return fmt.Errorf("execute OMR source schema DDL: %w", err)
	}
	for _, stmt := range splitStatements(schema.OMRSourceSeedDataSQL) {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			return fmt.Errorf("execute OMR source seed data: %w", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit: %w", err)
	}

	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = ON"); err != nil {
		return fmt.Errorf("re-enable foreign keys: %w", err)
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("read schema version: %w", err)
	}
	if ver != ApprovedOMRSourceVersion {
		return fmt.Errorf("OMR source baseline alembic_version = %q, want %q", ver, ApprovedOMRSourceVersion)
	}

	slog.Info("initialized OMR source intermediate database", "revision", ver)
	return nil
}
