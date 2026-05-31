package dbcore

import (
	"context"
	"database/sql"
	"fmt"
	"io"
	"log/slog"
)

// Bootstrap initializes a new database or upgrades an existing one to
// TargetVersion. It is safe to call on every startup — it is a no-op
// when the schema is already current.
func Bootstrap(ctx context.Context, db *sql.DB, dbPath string) error {
	var tableCount int
	err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount)
	if err != nil {
		return fmt.Errorf("check tables: %w", err)
	}

	if tableCount == 0 {
		slog.Info("initializing database")
		if err := InitDatabase(ctx, db, io.Discard); err != nil {
			return fmt.Errorf("init database: %w", err)
		}
		return nil
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("schema version: %w", err)
	}

	if ver == TargetVersion {
		return nil
	}

	slog.Info("upgrading database", "from", ver, "to", TargetVersion)

	backupPath, err := BackupDatabase(ctx, db, dbPath)
	if err != nil {
		return fmt.Errorf("backup: %w", err)
	}
	slog.Info("database backup created", "path", backupPath)

	if err := ApplyMigrations(ctx, db, ver, TargetVersion, io.Discard); err != nil {
		return fmt.Errorf("migrate (restore from %s): %w", backupPath, err)
	}

	_ = CleanOldBackups(dbPath, 3)
	return nil
}
