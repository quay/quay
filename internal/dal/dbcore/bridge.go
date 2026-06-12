package dbcore

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"strings"

	"github.com/quay/quay/internal/dal/schema"
)

// knownOMRVersions lists every Alembic version an OMR SQLite database could
// have. The bridge migration is safe to run from any of these starting points.
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
}

// bridgeColumns are columns that may be missing on existing tables in old OMR databases.
// New tables created by the bridge SQL already include all columns.
var bridgeColumns = []struct {
	table, column, typedef string
}{
	{"tag", "immutable", "BOOLEAN DEFAULT (0) NOT NULL"},
	{"manifest", "artifact_type", "VARCHAR(255)"},
	{"manifest", "artifact_type_backfilled", "BOOLEAN"},
	{"repomirrorconfig", "skopeo_timeout", "BIGINT DEFAULT '300' NOT NULL"},
	{"repomirrorconfig", "architecture_filter", "TEXT"},
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
// It validates the starting version, applies column additions and index fixes
// that SQLite cannot express idempotently, then executes the bridge SQL file.
func RunBridge(ctx context.Context, db *sql.DB, w io.Writer) error {
	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("read schema version: %w", err)
	}
	if ver == TargetVersion {
		fmt.Fprintf(w, "Schema is current (version %s)\n", ver)
		return nil
	}
	if !knownOMRVersions[ver] {
		return fmt.Errorf(
			"unknown schema version %q — this tool supports OMR v1.3.x/v1.4.x databases; "+
				"upgrade to a newer version of this binary or contact support", ver)
	}

	fmt.Fprintf(w, "Bridging schema from %s to %s\n", ver, TargetVersion)

	if _, err := db.ExecContext(ctx, "PRAGMA foreign_keys = OFF"); err != nil {
		return fmt.Errorf("disable foreign keys: %w", err)
	}
	defer func() { _, _ = db.ExecContext(ctx, "PRAGMA foreign_keys = ON") }()

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	if err := applyBridge(ctx, tx); err != nil {
		return err
	}

	if _, err := tx.ExecContext(ctx, "UPDATE alembic_version SET version_num = ?", TargetVersion); err != nil {
		return fmt.Errorf("stamp version: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit bridge: %w", err)
	}

	fmt.Fprintf(w, "Schema bridged to %s\n", TargetVersion)
	return nil
}

// applyBridge runs the three bridge steps within the given transaction:
// column additions, index fixes, and the bridge SQL file.
func applyBridge(ctx context.Context, tx *sql.Tx) error {
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

	bridgeSQL, err := schema.MigrationFiles.ReadFile("sqlite/migrations/0001_bridge_from_omr.sql")
	if err != nil {
		return fmt.Errorf("read bridge SQL: %w", err)
	}
	for _, stmt := range splitStatements(string(bridgeSQL)) {
		trimmed := strings.TrimSpace(stmt)
		if trimmed == "" || strings.HasPrefix(trimmed, "--") {
			continue
		}
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			return fmt.Errorf("execute bridge SQL: %w\nstatement: %s", err, truncate(trimmed, 200))
		}
	}

	return nil
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
