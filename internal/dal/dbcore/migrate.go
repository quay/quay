package dbcore

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/schema"
)

// BridgeTargetVersion is the Alembic HEAD revision produced by the OMR bridge
// before Go-only SQLite migrations are applied.
const BridgeTargetVersion = "9fa37f66a9b6"

const schemaConvergenceVersion = "9fdf045306b8"

// TargetVersion is the SQLite schema revision this binary expects.
const TargetVersion = schemaConvergenceVersion

// InitDatabase creates a fresh SQLite database from the generated bridge DDL
// and seed data, then applies Go-only migrations. It returns an error if the
// database file already contains tables (use Upgrade for existing databases).
func InitDatabase(ctx context.Context, db *sql.DB, w io.Writer) error {
	catalog, err := loadEmbeddedMigrationCatalog()
	if err != nil {
		return fmt.Errorf("load migration catalog: %w", err)
	}
	return initDatabaseWithSources(ctx, db, catalog, schema.QuaySchemaSQL, schema.SeedDataSQL, w)
}

func initDatabaseWithFS(ctx context.Context, db *sql.DB, migrationFS fs.FS, w io.Writer) error {
	catalog, err := loadMigrationCatalog(migrationFS)
	if err != nil {
		return fmt.Errorf("load migration catalog: %w", err)
	}
	if err := catalog.validateVersions(); err != nil {
		return fmt.Errorf("validate migration catalog: %w", err)
	}
	return initDatabaseWithSources(ctx, db, catalog, schema.QuaySchemaSQL, schema.SeedDataSQL, w)
}

func initDatabaseWithSources(
	ctx context.Context,
	db *sql.DB,
	catalog *migrationCatalog,
	schemaSQL, seedSQL string,
	w io.Writer,
) (retErr error) {
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
	foreignKeysDisabled := true
	defer func() {
		if !foreignKeysDisabled {
			return
		}
		if _, err := db.ExecContext(context.WithoutCancel(ctx), "PRAGMA foreign_keys = ON"); err != nil {
			retErr = errors.Join(retErr, fmt.Errorf("re-enable foreign keys: %w", err))
		}
	}()

	plan, err := initializeBaseSchema(ctx, db, catalog, schemaSQL, seedSQL)
	if err != nil {
		return err
	}
	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = ON"); err != nil {
		return fmt.Errorf("re-enable foreign keys before migrations: %w", err)
	}
	foreignKeysDisabled = false

	if err := applyMigrationPlan(ctx, db, plan, catalog.chainableCount(), w); err != nil {
		return fmt.Errorf("apply Go-only migrations: %w", err)
	}

	if err := verifyForeignKeys(ctx, db); err != nil {
		return err
	}

	writeInitSummary(ctx, db, w)
	return nil
}

func initializeBaseSchema(
	ctx context.Context,
	db *sql.DB,
	catalog *migrationCatalog,
	schemaSQL, seedSQL string,
) ([]migrationInfo, error) {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin transaction: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // no-op after commit

	if _, err := tx.ExecContext(ctx, schemaSQL); err != nil {
		return nil, fmt.Errorf("execute schema DDL: %w", err)
	}

	// Seed data: split on semicolons and execute each INSERT.
	// The embedded seed_data.sql contains one INSERT per line.
	for _, stmt := range splitStatements(seedSQL) {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			return nil, fmt.Errorf("execute seed data: %w", err)
		}
	}

	var seedVersion string
	if err := tx.QueryRowContext(ctx, "SELECT version_num FROM alembic_version").Scan(&seedVersion); err != nil {
		return nil, fmt.Errorf("read seeded schema version: %w", err)
	}
	plan, err := catalog.plan(seedVersion, TargetVersion)
	if err != nil {
		return nil, fmt.Errorf("plan Go-only migrations from seeded version %q: %w", seedVersion, err)
	}
	if err := verifyForeignKeys(ctx, tx); err != nil {
		return nil, fmt.Errorf("validate schema and seed data: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit: %w", err)
	}

	return plan, nil
}

func writeInitSummary(ctx context.Context, db *sql.DB, w io.Writer) {
	var tables int
	_ = db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tables)

	var seedRows int
	// Count rows in known seed tables to give a rough summary.
	seedTables := []string{
		"mediatype", "logentrykind", "visibility", "repositorykind", "tagkind",
		"loginservice", "buildtriggerservice", "accesstokenkind", "notificationkind",
		"externalnotificationevent", "externalnotificationmethod", "quayregion", "quayservice",
		"imagestoragelocation", "imagestoragetransformation", "imagestoragesignaturekind", "labelsourcetype",
	}
	for _, t := range seedTables {
		var n int
		_ = db.QueryRowContext(ctx, fmt.Sprintf("SELECT count(*) FROM %q", t)).Scan(&n)
		seedRows += n
	}

	fmt.Fprintf(w, "Initialized database: %d tables, %d seed rows\n", tables, seedRows)
}

type foreignKeyQueryer interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}

func verifyForeignKeys(ctx context.Context, queryer foreignKeyQueryer) error {
	rows, err := queryer.QueryContext(ctx, "PRAGMA foreign_key_check")
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
	catalog, err := loadEmbeddedMigrationCatalog()
	if err != nil {
		return
	}
	if len(catalog.migrations) == 0 {
		fmt.Fprintln(w, "No migration files found.")
		return
	}
	fmt.Fprintln(w, "Pending migrations:")
	for _, migration := range catalog.migrations {
		fmt.Fprintf(w, "  - %s\n", migration.filename)
	}
}

type migrationInfo struct {
	filename     string
	sql          string
	revision     string
	downRevision string
}

type migrationCatalog struct {
	migrations           []migrationInfo
	root                 migrationInfo
	migrationsByRevision map[string]migrationInfo
	migrationsByDown     map[string]migrationInfo
}

func loadEmbeddedMigrationCatalog() (*migrationCatalog, error) {
	migrationFS, err := fs.Sub(schema.MigrationFiles, "sqlite/migrations")
	if err != nil {
		return nil, fmt.Errorf("open migrations directory: %w", err)
	}
	catalog, err := loadMigrationCatalog(migrationFS)
	if err != nil {
		return nil, err
	}
	if err := catalog.validateVersions(); err != nil {
		return nil, err
	}
	return catalog, nil
}

func loadMigrationCatalog(migrationFS fs.FS) (*migrationCatalog, error) {
	entries, err := fs.ReadDir(migrationFS, ".")
	if err != nil {
		return nil, fmt.Errorf("read migrations directory: %w", err)
	}

	catalog := &migrationCatalog{
		migrationsByRevision: make(map[string]migrationInfo),
		migrationsByDown:     make(map[string]migrationInfo),
	}
	var roots []migrationInfo
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".sql") {
			continue
		}
		migrationSQL, err := fs.ReadFile(migrationFS, entry.Name())
		if err != nil {
			return nil, fmt.Errorf("read migration %s: %w", entry.Name(), err)
		}
		info, err := extractMigrationInfo(entry.Name(), string(migrationSQL))
		if err != nil {
			return nil, fmt.Errorf("migration %s: %w", entry.Name(), err)
		}
		if previous, ok := catalog.migrationsByRevision[info.revision]; ok {
			return nil, fmt.Errorf(
				"duplicate revision %q in %s and %s", info.revision, previous.filename, info.filename,
			)
		}
		if info.revision == info.downRevision {
			return nil, fmt.Errorf("migration %s has self-link revision %q", info.filename, info.revision)
		}

		catalog.migrations = append(catalog.migrations, info)
		catalog.migrationsByRevision[info.revision] = info
		if info.downRevision == "" {
			roots = append(roots, info)
			continue
		}
		if previous, ok := catalog.migrationsByDown[info.downRevision]; ok {
			return nil, fmt.Errorf(
				"duplicate down_revision %q in %s and %s",
				info.downRevision, previous.filename, info.filename,
			)
		}
		catalog.migrationsByDown[info.downRevision] = info
	}

	if err := catalog.validateStructure(roots); err != nil {
		return nil, err
	}
	return catalog, nil
}

func (catalog *migrationCatalog) validateStructure(roots []migrationInfo) error {
	if len(catalog.migrations) == 0 {
		return fmt.Errorf("no migration files found")
	}
	if len(roots) != 1 {
		return fmt.Errorf("migration catalog must contain exactly one bridge root; found %d", len(roots))
	}
	catalog.root = roots[0]
	for _, migration := range catalog.migrations {
		if migration.downRevision == "" {
			continue
		}
		if _, ok := catalog.migrationsByRevision[migration.downRevision]; !ok {
			return fmt.Errorf(
				"migration %s has dangling down_revision %q",
				migration.filename, migration.downRevision,
			)
		}
	}
	if err := catalog.validateAcyclic(); err != nil {
		return err
	}
	if _, err := catalog.terminalRevision(); err != nil {
		return err
	}
	return nil
}

func (catalog *migrationCatalog) validateAcyclic() error {
	const (
		visiting = 1
		visited  = 2
	)
	state := make(map[string]int, len(catalog.migrationsByRevision))
	var visit func(string) error
	visit = func(revision string) error {
		switch state[revision] {
		case visiting:
			return fmt.Errorf("migration catalog contains a cycle at revision %q", revision)
		case visited:
			return nil
		}
		state[revision] = visiting
		migration := catalog.migrationsByRevision[revision]
		if _, ok := catalog.migrationsByRevision[migration.downRevision]; ok {
			if err := visit(migration.downRevision); err != nil {
				return err
			}
		}
		state[revision] = visited
		return nil
	}
	for revision := range catalog.migrationsByRevision {
		if err := visit(revision); err != nil {
			return err
		}
	}
	return nil
}

func (catalog *migrationCatalog) terminalRevision() (string, error) {
	visited := make(map[string]bool, len(catalog.migrationsByRevision))
	revision := catalog.root.revision
	for {
		visited[revision] = true
		next, ok := catalog.migrationsByDown[revision]
		if !ok {
			break
		}
		revision = next.revision
	}
	if len(visited) != len(catalog.migrationsByRevision) {
		return "", fmt.Errorf(
			"migration catalog has %d revision(s) not connected to bridge root %q",
			len(catalog.migrationsByRevision)-len(visited), catalog.root.revision,
		)
	}
	return revision, nil
}

func (catalog *migrationCatalog) validateVersions() error {
	if catalog.root.revision != BridgeTargetVersion {
		return fmt.Errorf(
			"bridge root revision %q does not match BridgeTargetVersion %q",
			catalog.root.revision, BridgeTargetVersion,
		)
	}
	terminalRevision, err := catalog.terminalRevision()
	if err != nil {
		return err
	}
	if terminalRevision != TargetVersion {
		return fmt.Errorf(
			"migration catalog terminal revision %q does not match TargetVersion %q",
			terminalRevision, TargetVersion,
		)
	}
	return nil
}

func (catalog *migrationCatalog) plan(currentVersion, targetVersion string) ([]migrationInfo, error) {
	if _, ok := catalog.migrationsByRevision[targetVersion]; !ok {
		return nil, fmt.Errorf("target revision %q is unreachable from %q", targetVersion, currentVersion)
	}
	if _, ok := catalog.migrationsByRevision[currentVersion]; !ok {
		return nil, fmt.Errorf("current revision %q is not in the migration catalog", currentVersion)
	}

	var plan []migrationInfo
	seen := make(map[string]bool)
	for currentVersion != targetVersion {
		if seen[currentVersion] {
			return nil, fmt.Errorf("migration path contains a cycle at revision %q", currentVersion)
		}
		seen[currentVersion] = true
		next, ok := catalog.migrationsByDown[currentVersion]
		if !ok {
			return nil, fmt.Errorf("target revision %q is unreachable from %q", targetVersion, currentVersion)
		}
		plan = append(plan, next)
		currentVersion = next.revision
	}
	return plan, nil
}

func (catalog *migrationCatalog) chainableCount() int {
	return len(catalog.migrations) - 1
}

// ApplyMigrations reads embedded SQL migration files and applies the revision
// chain needed to bring the database from currentVersion to targetVersion.
// Each non-bridge migration must contain "-- revision: <id>" and
// "-- down_revision: <id>" comments.
func ApplyMigrations(ctx context.Context, db *sql.DB, currentVersion, targetVersion string, w io.Writer) error {
	catalog, err := loadEmbeddedMigrationCatalog()
	if err != nil {
		return fmt.Errorf("load migration catalog: %w", err)
	}
	return applyMigrationsWithCatalog(ctx, db, catalog, currentVersion, targetVersion, w)
}

func applyMigrationsWithFS(
	ctx context.Context,
	db *sql.DB,
	migrationFS fs.FS,
	currentVersion, targetVersion string,
	w io.Writer,
) error {
	catalog, err := loadMigrationCatalog(migrationFS)
	if err != nil {
		return fmt.Errorf("load migration catalog: %w", err)
	}
	return applyMigrationsWithCatalog(ctx, db, catalog, currentVersion, targetVersion, w)
}

func applyMigrationsWithCatalog(
	ctx context.Context,
	db *sql.DB,
	catalog *migrationCatalog,
	currentVersion, targetVersion string,
	w io.Writer,
) error {
	plan, err := catalog.plan(currentVersion, targetVersion)
	if err != nil {
		return err
	}
	return applyMigrationPlan(ctx, db, plan, catalog.chainableCount(), w)
}

func applyMigrationPlan(
	ctx context.Context, db *sql.DB, plan []migrationInfo, migrationCount int, w io.Writer,
) error {
	fmt.Fprintf(w, "Found %d migration file(s)\n", migrationCount)
	for _, info := range plan {
		fmt.Fprintf(w, "Applying: %s (revision %s)\n", info.filename, info.revision)

		if err := applyMigrationTx(ctx, db, info.sql, info.revision); err != nil {
			return fmt.Errorf("apply migration %s: %w", info.filename, err)
		}
		fmt.Fprintf(w, "Applied: %s\n", info.filename)
	}

	fmt.Fprintf(w, "Migration complete: %d migration(s) applied\n", len(plan))
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
	if revisionID == schemaConvergenceVersion {
		if err := convergeBridgeSchema(ctx, tx); err != nil {
			return fmt.Errorf("converge bridge schema: %w", err)
		}
	}
	if err := verifyForeignKeys(ctx, tx); err != nil {
		return fmt.Errorf("validate migration foreign keys: %w", err)
	}

	if _, err := tx.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", revisionID); err != nil {
		return fmt.Errorf("update alembic_version: %w", err)
	}

	return tx.Commit()
}

func extractMigrationInfo(filename, migrationSQL string) (migrationInfo, error) {
	info := migrationInfo{
		filename: filename,
		sql:      migrationSQL,
	}
	for _, line := range strings.Split(migrationSQL, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "-- revision:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) != 2 {
				return migrationInfo{}, fmt.Errorf("malformed revision comment: %s", line)
			}
			id := strings.TrimSpace(parts[1])
			if id == "" {
				return migrationInfo{}, fmt.Errorf("empty revision ID in comment: %s", line)
			}
			info.revision = id
		}
		if strings.HasPrefix(line, "-- down_revision:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) != 2 {
				return migrationInfo{}, fmt.Errorf("malformed down_revision comment: %s", line)
			}
			info.downRevision = strings.TrimSpace(parts[1])
		}
	}
	if info.revision == "" {
		return migrationInfo{}, fmt.Errorf("missing '-- revision: <id>' comment")
	}
	return info, nil
}

// splitStatements splits a SQL script on semicolons, trimming whitespace and
// discarding empty entries. It strips full-line "--" comments only; semicolons
// in inline comments are still treated as statement delimiters.
func splitStatements(rawSQL string) []string {
	var withoutComments strings.Builder
	for _, line := range strings.Split(rawSQL, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "--") {
			continue
		}
		withoutComments.WriteString(line)
		withoutComments.WriteByte('\n')
	}

	raw := strings.Split(withoutComments.String(), ";")
	stmts := make([]string, 0, len(raw))
	for _, s := range raw {
		s = strings.TrimSpace(s)
		if s != "" {
			stmts = append(stmts, s)
		}
	}
	return stmts
}
