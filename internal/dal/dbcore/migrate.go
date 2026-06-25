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
const TargetVersion = "b1a79fa8e630"

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

	dst, err := os.OpenFile(backupPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0o600) //nolint:gosec // path derived from dbPath
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

// ListMigrations prints the available migration files to w.
func ListMigrations(w io.Writer) {
	entries, err := schema.MigrationFiles.ReadDir("sqlite/migrations")
	if err != nil {
		return
	}
	found := false
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".sql") {
			if !found {
				fmt.Fprintln(w, "Pending migrations:")
				found = true
			}
			fmt.Fprintf(w, "  - %s\n", e.Name())
		}
	}
	if !found {
		fmt.Fprintln(w, "No migration files found.")
	}
}

// ApplyMigrations reads embedded SQL migration files and applies them in
// filename order to bring the database from currentVersion to targetVersion.
// Each migration runs in its own transaction and must contain a
// "-- revision: <id>" comment identifying the alembic version it produces.
func ApplyMigrations(ctx context.Context, db *sql.DB, currentVersion, targetVersion string, w io.Writer) error {
	entries, err := schema.MigrationFiles.ReadDir("sqlite/migrations")
	if err != nil {
		return fmt.Errorf("read migrations directory: %w", err)
	}

	var migrationFiles []string
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".sql") {
			continue
		}
		migrationFiles = append(migrationFiles, e.Name())
	}

	if len(migrationFiles) == 0 {
		return fmt.Errorf("no migration files found")
	}

	fmt.Fprintf(w, "Found %d migration file(s)\n", len(migrationFiles))

	applied := 0
	for _, filename := range migrationFiles {
		sqlBytes, err := schema.MigrationFiles.ReadFile("sqlite/migrations/" + filename)
		if err != nil {
			return fmt.Errorf("read migration %s: %w", filename, err)
		}

		migrationSQL := string(sqlBytes)
		revisionID, err := extractRevisionID(migrationSQL)
		if err != nil {
			return fmt.Errorf("migration %s: %w", filename, err)
		}

		if revisionID == currentVersion {
			continue
		}

		fmt.Fprintf(w, "Applying: %s (revision %s)\n", filename, revisionID)

		if err := applyMigrationTx(ctx, db, migrationSQL, revisionID); err != nil {
			return fmt.Errorf("apply migration %s: %w", filename, err)
		}

		applied++
		currentVersion = revisionID
		fmt.Fprintf(w, "Applied: %s\n", filename)

		if currentVersion == targetVersion {
			break
		}
	}

	if currentVersion != targetVersion {
		return fmt.Errorf("migrations completed but version mismatch: current=%s target=%s", currentVersion, targetVersion)
	}

	fmt.Fprintf(w, "Migration complete: %d migration(s) applied\n", applied)
	return nil
}

func applyMigrationTx(ctx context.Context, db *sql.DB, migrationSQL, revisionID string) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // no-op after commit

	for _, stmt := range splitStatements(migrationSQL) {
		trimmed := strings.TrimSpace(stmt)
		if trimmed == "" || strings.HasPrefix(trimmed, "--") {
			continue
		}
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			return fmt.Errorf("execute SQL: %w", err)
		}
	}

	if _, err := tx.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", revisionID); err != nil {
		return fmt.Errorf("update alembic_version: %w", err)
	}

	return tx.Commit()
}

func extractRevisionID(migrationSQL string) (string, error) {
	for _, line := range strings.Split(migrationSQL, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "-- revision:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) != 2 {
				return "", fmt.Errorf("malformed revision comment: %s", line)
			}
			id := strings.TrimSpace(parts[1])
			if id == "" {
				return "", fmt.Errorf("empty revision ID in comment: %s", line)
			}
			return id, nil
		}
	}
	return "", fmt.Errorf("missing '-- revision: <id>' comment")
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
