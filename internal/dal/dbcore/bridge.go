package dbcore

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"strings"
)

const (
	sqliteVarchar255Type    = "VARCHAR(255)"
	sqliteDateTimeType      = "DATETIME"
	manifestTable           = "manifest"
	repoMirrorConfigTable   = "repomirrorconfig"
	oauthAccessTokenTable   = "oauthaccesstoken"
	oauthCreatedColumn      = "created"
	oauthLastAccessedColumn = "last_accessed"
	oauthDisplayNameColumn  = "display_name"
	createOAuthAPILogKind   = "create_oauth_api_token"
	revokeOAuthAPILogKind   = "revoke_oauth_api_token"
)

// knownOMRVersions lists every Alembic version a supported OMR v2.0.x SQLite
// database could have. The bridge migration is safe to run from any of these
// starting points.
var knownOMRVersions = map[string]bool{
	// Quay 3.12.x era (OMR SQLite support introduced)
	"0cdd1f27a450": true,
	"0988213e0885": true,
	"66147b81aad2": true,
	"f67fe4871771": true,
	"2664723e1b4b": true,
	"8a7ba94c2e84": true,
	"3f8d7acdf7f9": true,
	// Versions in the bridge chain itself (partially upgraded DBs)
	"a32e17bfad20": true,
	"5b8dc452f5c3": true,
	"ba263f9be4a6": true,
	"9085e82074f2": true,
	"8e97c2cfee57": true,
	"3634f2df3c5b": true,
	"e8ed3fb547da": true,
	"1623f40582ed": true,
	"7078c84d14e8": true,
	"9307c3d604b4": true,
	"27d0df099ac4": true,
	"a1b2c3d4e5f6": true,
	"285f36ce97fd": true,
	"b2c3d4e5f6a7": true,
	"b1c2d3e4f5a6": true,
	"15f06d00c4b3": true,
	"414c5e2fc487": true,
	"c3d4e5f6a7b8": true,
	"b1a79fa8e630": true,
	"d064a4f00d4a": true,
	// OAuth API token metadata and display name
	"b30800b1d271": true,
	// Quota notification tables
	"6715e4719375": true,
	"9fa37f66a9b6": true,
}

// bridgeColumns are columns that may be missing on existing tables in old OMR databases.
// New tables created by the bridge SQL already include all columns.
var bridgeColumns = []struct {
	table, column, typedef string
}{
	{"tag", "immutable", "BOOLEAN DEFAULT (0) NOT NULL"},
	{manifestTable, "artifact_type", sqliteVarchar255Type},
	{manifestTable, "artifact_type_backfilled", "BOOLEAN"},
	{repoMirrorConfigTable, "skopeo_timeout", "BIGINT DEFAULT '300' NOT NULL"},
	{repoMirrorConfigTable, "architecture_filter", "TEXT"},
}

// bridgeIndexFixes are indexes that changed from UNIQUE to non-UNIQUE.
var bridgeIndexFixes = []struct {
	table, indexName, columns string
}{
	{"namespaceautoprunepolicy", "namespaceautoprunepolicy_namespace_id", "namespace_id"},
	{"repositoryautoprunepolicy", "repositoryautoprunepolicy_repository_id", "repository_id"},
	{"organizationrhskus", "organizationrhskus_subscription_id", "subscription_id"},
}

// RunBridge upgrades an OMR SQLite database to the Go binary's target schema.
// This is a Go-native squash migration for supported OMR Alembic revisions:
// the standalone binary intentionally does not ship Python, Alembic, or Quay's
// Python migration runtime. It validates the starting version, applies column
// additions and index fixes that SQLite cannot express idempotently, then
// executes the bridge SQL file.
func RunBridge(ctx context.Context, db *sql.DB, w io.Writer) error {
	catalog, err := loadEmbeddedMigrationCatalog()
	if err != nil {
		return fmt.Errorf("load migration catalog: %w", err)
	}
	return runBridgeWithCatalog(ctx, db, catalog, w)
}

func runBridgeWithFS(ctx context.Context, db *sql.DB, migrationFS fs.FS, w io.Writer) error {
	catalog, err := loadMigrationCatalog(migrationFS)
	if err != nil {
		return fmt.Errorf("load migration catalog: %w", err)
	}
	if err := catalog.validateVersions(); err != nil {
		return fmt.Errorf("validate migration catalog: %w", err)
	}
	return runBridgeWithCatalog(ctx, db, catalog, w)
}

func runBridgeWithCatalog(ctx context.Context, db *sql.DB, catalog *migrationCatalog, w io.Writer) error {
	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("read schema version: %w", err)
	}
	if ver == TargetVersion {
		fmt.Fprintf(w, "Schema is current (version %s)\n", ver)
		return nil
	}

	if _, isGoRevision := catalog.migrationsByRevision[ver]; isGoRevision {
		plan, err := catalog.plan(ver, TargetVersion)
		if err != nil {
			return fmt.Errorf("plan SQLite migrations: %w", err)
		}
		fmt.Fprintf(w, "Migrating SQLite schema from %s to %s\n", ver, TargetVersion)
		if err := applyMigrationPlan(ctx, db, plan, catalog.chainableCount(), w); err != nil {
			return fmt.Errorf("apply SQLite migrations: %w", err)
		}
		return nil
	}

	if !knownOMRVersions[ver] {
		return fmt.Errorf(
			"unknown schema version %q — this tool supports OMR v2.0.x (SQLite) databases; "+
				"if you are on OMR v1.3.x, upgrade to OMR v2.0 first", ver)
	}

	plan, err := catalog.plan(catalog.root.revision, TargetVersion)
	if err != nil {
		return fmt.Errorf("plan post-bridge SQLite migrations: %w", err)
	}
	if err := bridgeToRoot(ctx, db, ver, catalog.root, w); err != nil {
		return err
	}

	fmt.Fprintf(w, "Migrating SQLite schema from %s to %s\n", catalog.root.revision, TargetVersion)
	if err := applyMigrationPlan(ctx, db, plan, catalog.chainableCount(), w); err != nil {
		return fmt.Errorf("apply SQLite migrations: %w", err)
	}
	return nil
}

func bridgeToRoot(
	ctx context.Context, db *sql.DB, currentVersion string, bridgeRoot migrationInfo, w io.Writer,
) error {
	return bridgeToRootWithApply(ctx, db, currentVersion, bridgeRoot, w, applyBridge)
}

func bridgeToRootWithApply(
	ctx context.Context,
	db *sql.DB,
	currentVersion string,
	bridgeRoot migrationInfo,
	w io.Writer,
	apply func(context.Context, *sql.Tx, string) error,
) (retErr error) {
	fmt.Fprintf(w, "Bridging schema from %s to %s\n", currentVersion, bridgeRoot.revision)

	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = OFF"); err != nil {
		return fmt.Errorf("disable foreign keys: %w", err)
	}
	defer func() {
		if _, err := db.ExecContext(context.WithoutCancel(ctx), "PRAGMA foreign_keys = ON"); err != nil {
			retErr = errors.Join(retErr, fmt.Errorf("re-enable foreign keys: %w", err))
		}
	}()

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	if err := apply(ctx, tx, bridgeRoot.sql); err != nil {
		return err
	}
	if err := verifyForeignKeys(ctx, tx); err != nil {
		return fmt.Errorf("validate bridge foreign keys: %w", err)
	}

	if _, err := tx.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", bridgeRoot.revision); err != nil {
		return fmt.Errorf("stamp version: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit bridge: %w", err)
	}

	fmt.Fprintf(w, "Schema bridged to %s\n", bridgeRoot.revision)
	return nil
}

// applyBridge runs the three bridge steps within the given transaction:
// column additions, index fixes, and the bridge SQL file.
func applyBridge(ctx context.Context, tx *sql.Tx, bridgeSQL string) error {
	for _, col := range bridgeColumns {
		if err := ensureColumn(ctx, tx, col.table, col.column, col.typedef); err != nil {
			return fmt.Errorf("ensure column %s.%s: %w", col.table, col.column, err)
		}
	}

	for _, idx := range bridgeIndexFixes {
		if err := ensureNonUniqueIndex(ctx, tx, idx.table, idx.indexName, idx.columns); err != nil {
			return fmt.Errorf("fix index %s: %w", idx.indexName, err)
		}
	}

	for _, stmt := range splitStatements(bridgeSQL) {
		trimmed := strings.TrimSpace(stmt)
		if trimmed == "" || strings.HasPrefix(trimmed, "--") {
			continue
		}
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			return fmt.Errorf("execute bridge SQL: %w\nstatement: %s", err, truncate(trimmed, 200))
		}
	}
	if err := convergeBridgeSchema(ctx, tx); err != nil {
		return fmt.Errorf("converge bridge schema: %w", err)
	}

	return nil
}

// convergeBridgeSchema applies the SQLite equivalents of the Alembic
// b1a79fa8e630, d064a4f00d4a, and b30800b1d271 migrations while bridging
// historical OMR databases.
func convergeBridgeSchema(ctx context.Context, tx *sql.Tx) error {
	for _, col := range []struct {
		name, typedef string
	}{
		{name: oauthLastAccessedColumn, typedef: sqliteDateTimeType},
		{name: oauthCreatedColumn, typedef: sqliteDateTimeType},
		{name: oauthDisplayNameColumn, typedef: sqliteVarchar255Type},
	} {
		if err := ensureColumn(ctx, tx, oauthAccessTokenTable, col.name, col.typedef); err != nil {
			return fmt.Errorf("ensure oauthaccesstoken.%s: %w", col.name, err)
		}
	}

	indexes := []struct {
		name, createSQL string
	}{
		{
			name: "user_email_unique_non_org",
			createSQL: `CREATE UNIQUE INDEX user_email_unique_non_org ` +
				`ON "user"(email) WHERE organization = false`,
		},
		{
			name:      "user_email_idx",
			createSQL: `CREATE INDEX user_email_idx ON user (email)`,
		},
		{
			name: "oauthaccesstoken_application_id_last_accessed",
			createSQL: `CREATE INDEX oauthaccesstoken_application_id_last_accessed ` +
				`ON oauthaccesstoken (application_id, last_accessed)`,
		},
	}
	for _, index := range indexes {
		if err := ensureIndexDefinition(ctx, tx, index.name, index.createSQL); err != nil {
			return fmt.Errorf("ensure index %s: %w", index.name, err)
		}
	}

	if _, err := tx.ExecContext(ctx, `DROP INDEX IF EXISTS user_email`); err != nil {
		return fmt.Errorf("drop full user email index: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE "user"
		SET email = (
			SELECT contact_email
			FROM organizationcontactemail
			WHERE organization_id = "user".id
				AND contact_email IS NOT NULL
		)
		WHERE organization = true
			AND email NOT LIKE '%@%'
			AND EXISTS (
				SELECT 1
				FROM organizationcontactemail
				WHERE organization_id = "user".id
					AND contact_email IS NOT NULL
			)
	`); err != nil {
		return fmt.Errorf("restore organization contact emails: %w", err)
	}

	for _, kind := range []string{createOAuthAPILogKind, revokeOAuthAPILogKind} {
		if _, err := tx.ExecContext(ctx,
			`INSERT OR IGNORE INTO logentrykind (name) VALUES (?)`, kind,
		); err != nil {
			return fmt.Errorf("seed log entry kind %s: %w", kind, err)
		}
	}
	return nil
}

func ensureIndexDefinition(ctx context.Context, tx *sql.Tx, indexName, createSQL string) error {
	var existingSQL sql.NullString
	err := tx.QueryRowContext(ctx,
		`SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?`, indexName,
	).Scan(&existingSQL)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("query index: %w", err)
	}
	if err == nil && existingSQL.Valid && canonicalSQL(existingSQL.String) == canonicalSQL(createSQL) {
		return nil
	}
	if err == nil {
		if _, err := tx.ExecContext(ctx, `DROP INDEX `+indexName); err != nil {
			return fmt.Errorf("drop incorrect index: %w", err)
		}
	}
	if _, err := tx.ExecContext(ctx, createSQL); err != nil {
		return fmt.Errorf("create index: %w", err)
	}
	return nil
}

func canonicalSQL(raw string) string {
	return strings.ToUpper(strings.Join(strings.Fields(raw), " "))
}

// ensureColumn adds a column to a table if it does not already exist.
func ensureColumn(ctx context.Context, tx *sql.Tx, table, column, typedef string) error {
	rows, err := tx.QueryContext(ctx, fmt.Sprintf("PRAGMA table_info(%q)", table))
	if err != nil {
		return fmt.Errorf("table_info %s: %w", table, err)
	}
	defer func() { _ = rows.Close() }()

	for rows.Next() {
		var cid int
		var name, colType string
		var notNull, pk int
		var dflt sql.NullString
		if err := rows.Scan(&cid, &name, &colType, &notNull, &dflt, &pk); err != nil {
			return fmt.Errorf("scan table_info: %w", err)
		}
		if strings.EqualFold(name, column) {
			return nil // column already exists
		}
	}
	if err := rows.Err(); err != nil {
		return err
	}

	stmt := fmt.Sprintf("ALTER TABLE %q ADD COLUMN %s %s", table, column, typedef)
	if _, err := tx.ExecContext(ctx, stmt); err != nil {
		return fmt.Errorf("add column: %w", err)
	}
	return nil
}

// ensureNonUniqueIndex checks if an index exists as UNIQUE and recreates it
// as non-UNIQUE if needed.
func ensureNonUniqueIndex(ctx context.Context, tx *sql.Tx, table, indexName, columns string) error {
	var indexSQL sql.NullString
	err := tx.QueryRowContext(ctx,
		"SELECT sql FROM sqlite_master WHERE type='index' AND name=?", indexName,
	).Scan(&indexSQL)

	if errors.Is(err, sql.ErrNoRows) || !indexSQL.Valid {
		// Index doesn't exist — create it.
		_, err = tx.ExecContext(ctx, fmt.Sprintf("CREATE INDEX %s ON %s (%s)", indexName, table, columns))
		return err
	}
	if err != nil {
		return fmt.Errorf("query index %s: %w", indexName, err)
	}

	if strings.Contains(strings.ToUpper(indexSQL.String), "UNIQUE") {
		// Wrong uniqueness — drop and recreate.
		if _, err := tx.ExecContext(ctx, "DROP INDEX "+indexName); err != nil {
			return fmt.Errorf("drop index %s: %w", indexName, err)
		}
		if _, err := tx.ExecContext(ctx, fmt.Sprintf("CREATE INDEX %s ON %s (%s)", indexName, table, columns)); err != nil {
			return fmt.Errorf("recreate index %s: %w", indexName, err)
		}
	}

	return nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
