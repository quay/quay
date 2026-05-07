package dbcore

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/schema"
)

// TargetVersion is the alembic HEAD revision this binary was built against.
// Updated by make go-schema when schema changes.
const TargetVersion = "c3d4e5f6a7b8"

// InitDatabase creates a fresh SQLite database by executing the embedded DDL
// and seed data. It returns an error if the database file already contains
// tables (use Upgrade for existing databases).
func InitDatabase(ctx context.Context, db *sql.DB, w io.Writer) error {
	// Check if database already has tables.
	var tableCount int
	err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount)
	if err != nil {
		return fmt.Errorf("check existing tables: %w", err)
	}
	if tableCount > 0 {
		return fmt.Errorf("database already contains %d tables; use 'quay db upgrade' instead", tableCount)
	}

	// Disable FK checks during schema creation (some CREATE TABLE statements
	// reference tables defined later in the DDL). PRAGMA foreign_keys must be
	// set outside a transaction — SQLite ignores it inside BEGIN/COMMIT.
	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = OFF"); err != nil {
		return fmt.Errorf("disable foreign keys: %w", err)
	}

	// Execute DDL in a transaction.
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // no-op after commit

	if _, err := tx.ExecContext(ctx, schema.QuaySchemaSQL); err != nil {
		return fmt.Errorf("execute schema DDL: %w", err)
	}

	// Seed data: split on semicolons and execute each INSERT.
	// The embedded seed_data.sql contains one INSERT per line.
	for _, stmt := range splitStatements(schema.SeedDataSQL) {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			return fmt.Errorf("execute seed data: %w", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit: %w", err)
	}

	// Re-enable FK checks and verify referential integrity.
	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = ON"); err != nil {
		return fmt.Errorf("re-enable foreign keys: %w", err)
	}

	rows, err := db.QueryContext(ctx, "PRAGMA foreign_key_check")
	if err != nil {
		return fmt.Errorf("foreign key check: %w", err)
	}
	defer func() { _ = rows.Close() }()
	if rows.Next() {
		var table, rowid, parent, fkid string
		if err := rows.Scan(&table, &rowid, &parent, &fkid); err != nil {
			return fmt.Errorf("scan FK violation: %w", err)
		}
		return fmt.Errorf("foreign key violation: table=%s rowid=%s parent=%s", table, rowid, parent)
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("foreign key check iteration: %w", err)
	}

	// Count tables and seed rows for summary.
	var tables int
	_ = db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tables)

	var seedRows int
	// Count rows in known seed tables to give a rough summary.
	seedTables := []string{"mediatype", "logentrykind", "visibility", "repositorykind", "tagkind",
		"loginservice", "buildtriggerservice", "accesstokenkind", "notificationkind",
		"externalnotificationevent", "externalnotificationmethod", "quayregion", "quayservice",
		"imagestoragelocation", "imagestoragetransformation", "imagestoragesignaturekind", "labelsourcetype"}
	for _, t := range seedTables {
		var n int
		_ = db.QueryRowContext(ctx, fmt.Sprintf("SELECT count(*) FROM %q", t)).Scan(&n)
		seedRows += n
	}

	fmt.Fprintf(w, "Initialized database: %d tables, %d seed rows\n", tables, seedRows)
	return nil
}

// SchemaVersion returns the current Alembic migration version from the
// database, or an empty string if the alembic_version table doesn't exist.
func SchemaVersion(ctx context.Context, db *sql.DB) (string, error) {
	q := daldb.New(db)
	ver, err := q.GetAlembicVersion(ctx)
	if err != nil {
		if strings.Contains(err.Error(), "no such table") {
			return "", nil
		}
		if errors.Is(err, sql.ErrNoRows) {
			return "", nil
		}
		return "", fmt.Errorf("query alembic_version: %w", err)
	}
	return ver, nil
}

// BackupDatabase creates a timestamped copy of the SQLite database file.
// Returns the backup file path.
func BackupDatabase(ctx context.Context, db *sql.DB, dbPath string) (string, error) {
	// Flush WAL to main database file so the backup is complete.
	if _, err := db.ExecContext(ctx, "PRAGMA wal_checkpoint(TRUNCATE)"); err != nil {
		return "", fmt.Errorf("wal checkpoint: %w", err)
	}

	ts := time.Now().UTC().Format("20060102T150405Z")
	backupPath := fmt.Sprintf("%s.backup-%s", dbPath, ts)

	src, err := os.Open(dbPath) //nolint:gosec // path from caller, not user input
	if err != nil {
		return "", fmt.Errorf("open source: %w", err)
	}
	defer func() { _ = src.Close() }()

	dst, err := os.Create(backupPath) //nolint:gosec // path derived from dbPath
	if err != nil {
		return "", fmt.Errorf("create backup: %w", err)
	}
	defer func() { _ = dst.Close() }()

	if _, err := io.Copy(dst, src); err != nil {
		return "", fmt.Errorf("copy: %w", err)
	}

	return backupPath, nil
}

// IntegrityCheck runs PRAGMA integrity_check on the database and returns
// an error if the result is anything other than "ok".
func IntegrityCheck(ctx context.Context, db *sql.DB) error {
	var result string
	if err := db.QueryRowContext(ctx, "PRAGMA integrity_check").Scan(&result); err != nil {
		return fmt.Errorf("integrity check: %w", err)
	}
	if result != "ok" {
		return fmt.Errorf("integrity check failed: %s", result)
	}
	return nil
}

// CleanOldBackups removes backups of dbPath older than the most recent keep count.
func CleanOldBackups(dbPath string, keep int) error {
	dir := filepath.Dir(dbPath)
	base := filepath.Base(dbPath) + ".backup-"

	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}

	var backups []string
	for _, e := range entries {
		if strings.HasPrefix(e.Name(), base) {
			backups = append(backups, filepath.Join(dir, e.Name()))
		}
	}

	// Filenames include timestamps, so lexicographic sort = chronological.
	// Remove oldest, keeping the most recent.
	if len(backups) <= keep {
		return nil
	}

	for _, b := range backups[:len(backups)-keep] {
		_ = os.Remove(b)
	}

	return nil
}

// splitStatements splits a SQL script on semicolons, trimming whitespace
// and discarding empty entries.
func splitStatements(rawSQL string) []string {
	raw := strings.Split(rawSQL, ";")
	stmts := make([]string, 0, len(raw))
	for _, s := range raw {
		s = strings.TrimSpace(s)
		if s != "" {
			stmts = append(stmts, s)
		}
	}
	return stmts
}
