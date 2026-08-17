package postgres

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
)

const (
	sqliteTimestampLayout = "2006-01-02 15:04:05.999999"
	sqliteDateLayout      = "2006-01-02"
)

const schemaInventorySQL = `
SELECT c.relname, c.relkind::text,
       row_number() OVER (PARTITION BY c.oid ORDER BY a.attnum),
       a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod), a.attnotnull
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
JOIN pg_catalog.pg_attribute AS a ON a.attrelid = c.oid
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY c.relname COLLATE "C", a.attnum`

// TableCopyCount records source and destination row counts for one table.
type TableCopyCount struct {
	SourceRows int64
	DestRows   int64
}

// CopyReport records non-secret copy counts by table.
type CopyReport struct {
	Tables map[string]TableCopyCount
}

type schemaColumn struct {
	table          string
	relationKind   string
	logicalOrdinal int64
	name           string
	postgresType   string
	notNull        bool
}

// CopyPostgresToSQLite streams the frozen PostgreSQL profile into an
// initialized OMR v2 SQLite intermediate in one transaction.
func CopyPostgresToSQLite(ctx context.Context, pg *pgx.Conn, sqliteDB *sql.DB) (CopyReport, error) {
	report := CopyReport{Tables: make(map[string]TableCopyCount, len(approvedPostgresProfile.Tables))}

	pgTx, err := pg.BeginTx(ctx, pgx.TxOptions{
		IsoLevel:   pgx.RepeatableRead,
		AccessMode: pgx.ReadOnly,
	})
	if err != nil {
		return report, fmt.Errorf("begin postgres snapshot transaction: %w", err)
	}
	defer func() { _ = pgTx.Rollback(ctx) }()

	if err := validateSource(ctx, pgTx); err != nil {
		return report, fmt.Errorf("validate postgres source: %w", err)
	}

	if _, err := sqliteDB.ExecContext(ctx, "PRAGMA foreign_keys = OFF"); err != nil {
		return report, fmt.Errorf("disable sqlite foreign keys: %w", err)
	}
	defer func() { _, _ = sqliteDB.ExecContext(ctx, "PRAGMA foreign_keys = ON") }()

	sqliteTx, err := sqliteDB.BeginTx(ctx, nil)
	if err != nil {
		return report, fmt.Errorf("begin sqlite transaction: %w", err)
	}
	defer func() { _ = sqliteTx.Rollback() }() //nolint:errcheck // No-op after commit.

	var totalRows int64
	for _, table := range approvedPostgresProfile.Tables {
		count, err := copyTable(ctx, pgTx, sqliteTx, table)
		if err != nil {
			return report, fmt.Errorf("copy table %q: %w", table.Name, err)
		}
		report.Tables[table.Name] = count
		totalRows += count.DestRows
		slog.Debug("copied PostgreSQL table", "table", table.Name, "rows", count.DestRows)
	}

	if err := foreignKeyCheckSQLite(ctx, sqliteTx); err != nil {
		return report, fmt.Errorf("post-copy foreign key check: %w", err)
	}
	if err := integrityCheckSQLite(ctx, sqliteTx); err != nil {
		return report, fmt.Errorf("post-copy integrity check: %w", err)
	}
	if err := sqliteTx.Commit(); err != nil {
		return report, fmt.Errorf("commit sqlite transaction: %w", err)
	}
	if _, err := sqliteDB.ExecContext(ctx, "PRAGMA foreign_keys = ON"); err != nil {
		return report, fmt.Errorf("re-enable sqlite foreign keys: %w", err)
	}

	slog.Info("copied PostgreSQL source", "tables", len(report.Tables), "rows", totalRows)
	return report, nil
}

func validateSource(ctx context.Context, pgTx pgx.Tx) error {
	rows, err := pgTx.Query(ctx, `SELECT version_num FROM public.alembic_version`)
	if err != nil {
		return fmt.Errorf("read alembic revision: %w", err)
	}
	defer rows.Close()
	if !rows.Next() {
		if err := rows.Err(); err != nil {
			return fmt.Errorf("read alembic revision: %w", err)
		}
		return fmt.Errorf("expected exactly one alembic revision")
	}
	var revision string
	if err := rows.Scan(&revision); err != nil {
		return fmt.Errorf("scan alembic revision: %w", err)
	}
	if rows.Next() {
		return fmt.Errorf("expected exactly one alembic revision")
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("read alembic revision: %w", err)
	}
	if revision != approvedPostgresProfile.SchemaRevision {
		return fmt.Errorf("source alembic revision does not match the frozen profile")
	}

	inventory, err := readSchemaInventory(ctx, pgTx)
	if err != nil {
		return err
	}
	gotFingerprint := schemaFingerprint(inventory)
	if gotFingerprint != approvedPostgresProfile.SchemaFingerprint {
		return fmt.Errorf("source schema fingerprint %s does not match approved fingerprint %s", gotFingerprint, approvedPostgresProfile.SchemaFingerprint)
	}
	if err := validateProfileContract(inventory); err != nil {
		return fmt.Errorf("validate frozen profile contract: %w", err)
	}
	return nil
}

func readSchemaInventory(ctx context.Context, pgTx pgx.Tx) ([]schemaColumn, error) {
	rows, err := pgTx.Query(ctx, schemaInventorySQL)
	if err != nil {
		return nil, fmt.Errorf("query schema inventory: %w", err)
	}
	defer rows.Close()

	var inventory []schemaColumn
	for rows.Next() {
		var column schemaColumn
		if err := rows.Scan(&column.table, &column.relationKind, &column.logicalOrdinal, &column.name, &column.postgresType, &column.notNull); err != nil {
			return nil, fmt.Errorf("scan schema inventory: %w", err)
		}
		inventory = append(inventory, column)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate schema inventory: %w", err)
	}
	return inventory, nil
}

func schemaFingerprint(inventory []schemaColumn) string {
	h := sha256.New()
	for _, column := range inventory {
		fmt.Fprintf(h, "%s\x00%s\x00%d\x00%s\x00%s\x00%t\n", column.table, column.relationKind, column.logicalOrdinal, column.name, column.postgresType, column.notNull)
	}
	return hex.EncodeToString(h.Sum(nil))
}

func validateProfileContract(inventory []schemaColumn) error {
	inventoryIndex := 0
	for _, table := range approvedPostgresProfile.Tables {
		for inventoryIndex < len(inventory) && inventory[inventoryIndex].table == alembicVersionTable {
			inventoryIndex++
		}
		for _, column := range table.Columns {
			if inventoryIndex >= len(inventory) {
				return fmt.Errorf("profile has more columns than the approved schema inventory")
			}
			observed := inventory[inventoryIndex]
			if observed.table != table.Name || observed.name != column.Name || observed.postgresType != column.PostgresType {
				return fmt.Errorf("profile table or column metadata differs from the approved schema inventory")
			}
			inventoryIndex++
		}
	}
	for inventoryIndex < len(inventory) && inventory[inventoryIndex].table == alembicVersionTable {
		inventoryIndex++
	}
	if inventoryIndex != len(inventory) {
		return fmt.Errorf("profile has fewer columns than the approved schema inventory")
	}
	return nil
}

func copyTable(ctx context.Context, pgTx pgx.Tx, sqliteTx *sql.Tx, table postgresTable) (TableCopyCount, error) {
	var count TableCopyCount
	pgIdent := pgx.Identifier{"public", table.Name}.Sanitize()

	if err := pgTx.QueryRow(ctx, fmt.Sprintf("SELECT count(*) FROM %s", pgIdent)).Scan(&count.SourceRows); err != nil {
		return count, fmt.Errorf("count source rows: %w", err)
	}

	colNames := make([]string, len(table.Columns))
	placeholders := make([]string, len(table.Columns))
	for i, column := range table.Columns {
		colNames[i] = quoteSQLiteIdent(column.Name)
		placeholders[i] = "?"
	}
	//nolint:gosec // Identifiers come from the frozen profile; values are bound.
	insertSQL := fmt.Sprintf(
		"INSERT INTO %s (%s) VALUES (%s)",
		quoteSQLiteIdent(table.Name),
		strings.Join(colNames, ", "),
		strings.Join(placeholders, ", "),
	)
	stmt, err := sqliteTx.PrepareContext(ctx, insertSQL)
	if err != nil {
		return count, fmt.Errorf("prepare insert: %w", err)
	}
	defer func() { _ = stmt.Close() }()

	selectSQL := fmt.Sprintf("SELECT %s FROM %s", strings.Join(pgColumnIdents(table.Columns), ", "), pgIdent)
	rows, err := pgTx.Query(ctx, selectSQL)
	if err != nil {
		return count, fmt.Errorf("query source rows: %w", err)
	}
	defer rows.Close()

	args := make([]any, len(table.Columns))
	var insertedRows int64
	for rows.Next() {
		if err := ctx.Err(); err != nil {
			return count, err
		}

		values, err := rows.Values()
		if err != nil {
			return count, fmt.Errorf("read row values: %w", err)
		}
		if len(values) != len(table.Columns) {
			return count, fmt.Errorf("expected %d columns, got %d", len(table.Columns), len(values))
		}

		for i, column := range table.Columns {
			converted, err := convertColumnValue(column, values[i])
			if err != nil {
				return count, fmt.Errorf("column %q: %w", column.Name, err)
			}
			args[i] = converted
		}

		if _, err := stmt.ExecContext(ctx, args...); err != nil {
			return count, fmt.Errorf("insert row: %w", err)
		}
		insertedRows++
	}
	if err := rows.Err(); err != nil {
		return count, fmt.Errorf("iterate source rows: %w", err)
	}
	if insertedRows != count.SourceRows {
		return count, fmt.Errorf("inserted %d rows but source reported %d", insertedRows, count.SourceRows)
	}

	count.DestRows, err = validatedDestinationCount(ctx, sqliteTx, table.Name, count.SourceRows)
	if err != nil {
		return count, err
	}
	return count, nil
}

func validatedDestinationCount(ctx context.Context, tx *sql.Tx, table string, sourceRows int64) (int64, error) {
	var destinationRows int64
	//nolint:gosec // The table name comes from the frozen profile.
	if err := tx.QueryRowContext(ctx, "SELECT count(*) FROM "+quoteSQLiteIdent(table)).Scan(&destinationRows); err != nil {
		return 0, fmt.Errorf("count destination rows: %w", err)
	}
	if destinationRows != sourceRows {
		return 0, fmt.Errorf("destination has %d rows but source reported %d", destinationRows, sourceRows)
	}
	return destinationRows, nil
}

func convertColumnValue(column postgresColumn, value any) (any, error) {
	if value == nil {
		return nil, nil //nolint:nilnil // SQL NULL is a successful conversion.
	}

	switch column.Kind {
	case kindInt64:
		return convertInteger(value)
	case kindText:
		if typed, ok := value.(string); ok {
			return typed, nil
		}
		return nil, fmt.Errorf("expected string, got %T", value)
	case kindBool:
		if typed, ok := value.(bool); ok {
			if typed {
				return int64(1), nil
			}
			return int64(0), nil
		}
		return nil, fmt.Errorf("expected bool, got %T", value)
	case kindTimestamp:
		typed, ok := value.(time.Time)
		if !ok {
			return nil, fmt.Errorf("expected time.Time, got %T", value)
		}
		if column.PostgresType == postgresTypeDate {
			return typed.Format(sqliteDateLayout), nil
		}
		return typed.Format(sqliteTimestampLayout), nil
	case kindBytes:
		if typed, ok := value.([]byte); ok {
			return typed, nil
		}
		return nil, fmt.Errorf("expected []byte, got %T", value)
	default:
		return nil, fmt.Errorf("unsupported frozen column kind %q", column.Kind)
	}
}

func convertInteger(value any) (int64, error) {
	switch typed := value.(type) {
	case int64:
		return typed, nil
	case int32:
		return int64(typed), nil
	case int16:
		return int64(typed), nil
	default:
		return 0, fmt.Errorf("expected integer, got %T", value)
	}
}

func pgColumnIdents(columns []postgresColumn) []string {
	idents := make([]string, len(columns))
	for i, column := range columns {
		idents[i] = pgx.Identifier{column.Name}.Sanitize()
	}
	return idents
}

func quoteSQLiteIdent(name string) string {
	return fmt.Sprintf("%q", name)
}

func foreignKeyCheckSQLite(ctx context.Context, tx *sql.Tx) error {
	rows, err := tx.QueryContext(ctx, "PRAGMA foreign_key_check")
	if err != nil {
		return err
	}
	defer func() { _ = rows.Close() }()

	if rows.Next() {
		var table, rowID, parent, foreignKeyID string
		if err := rows.Scan(&table, &rowID, &parent, &foreignKeyID); err != nil {
			return fmt.Errorf("scan violation: %w", err)
		}
		return fmt.Errorf("violation in %s row %s referencing %s", table, rowID, parent)
	}
	return rows.Err()
}

func integrityCheckSQLite(ctx context.Context, tx *sql.Tx) error {
	var result string
	if err := tx.QueryRowContext(ctx, "PRAGMA integrity_check").Scan(&result); err != nil {
		return fmt.Errorf("integrity check: %w", err)
	}
	if result != "ok" {
		return fmt.Errorf("integrity check failed: %s", result)
	}
	return nil
}
