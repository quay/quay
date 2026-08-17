package postgres

import (
	"context"
	"database/sql"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
)

const sqliteTimestampLayout = "2006-01-02 15:04:05.999999"

// TableCopyCount records source and destination row counts for one table.
type TableCopyCount struct {
	SourceRows int64
	DestRows   int64
}

// CopyReport records non-secret copy counts by table.
type CopyReport struct {
	Tables map[string]TableCopyCount
}

// CopyPostgresToSQLite streams the approved PostgreSQL profile into an
// initialized OMR v2 SQLite intermediate in one transaction.
func CopyPostgresToSQLite(ctx context.Context, pg *pgx.Conn, sqliteDB *sql.DB, w io.Writer) (CopyReport, error) {
	report := CopyReport{Tables: make(map[string]TableCopyCount, len(approvedPostgresTables))}

	pgTx, err := pg.BeginTx(ctx, pgx.TxOptions{
		IsoLevel:   pgx.RepeatableRead,
		AccessMode: pgx.ReadOnly,
	})
	if err != nil {
		return report, fmt.Errorf("begin postgres snapshot transaction: %w", err)
	}
	defer func() { _ = pgTx.Rollback(ctx) }()

	if _, err := sqliteDB.ExecContext(ctx, "PRAGMA foreign_keys = OFF"); err != nil {
		return report, fmt.Errorf("disable sqlite foreign keys: %w", err)
	}
	defer func() { _, _ = sqliteDB.ExecContext(ctx, "PRAGMA foreign_keys = ON") }()

	sqliteTx, err := sqliteDB.BeginTx(ctx, nil)
	if err != nil {
		return report, fmt.Errorf("begin sqlite transaction: %w", err)
	}
	defer func() { _ = sqliteTx.Rollback() }() //nolint:errcheck // No-op after commit.

	for _, table := range approvedPostgresTables {
		if table.replacesBaselineSeed {
			//nolint:gosec // The table name comes from the compiled-in profile.
			if _, err := sqliteTx.ExecContext(ctx, "DELETE FROM "+quoteSQLiteIdent(table.name)); err != nil {
				return report, fmt.Errorf("clear baseline seed for table %s: %w", table.name, err)
			}
		}

		count, err := copyTable(ctx, pgTx, sqliteTx, table)
		if err != nil {
			return report, fmt.Errorf("copy table %s: %w", table.name, err)
		}
		report.Tables[table.name] = count
		fmt.Fprintf(w, "copied %s: %d rows\n", table.name, count.DestRows)
	}

	if err := sqliteTx.Commit(); err != nil {
		return report, fmt.Errorf("commit sqlite transaction: %w", err)
	}
	if _, err := sqliteDB.ExecContext(ctx, "PRAGMA foreign_keys = ON"); err != nil {
		return report, fmt.Errorf("re-enable sqlite foreign keys: %w", err)
	}
	if err := foreignKeyCheckSQLite(ctx, sqliteDB); err != nil {
		return report, fmt.Errorf("post-copy foreign key check: %w", err)
	}
	if err := integrityCheckSQLite(ctx, sqliteDB); err != nil {
		return report, fmt.Errorf("post-copy integrity check: %w", err)
	}

	return report, nil
}

func copyTable(ctx context.Context, pgTx pgx.Tx, sqliteTx *sql.Tx, table postgresTable) (TableCopyCount, error) {
	var count TableCopyCount
	pgIdent := pgx.Identifier{table.name}.Sanitize()

	if err := pgTx.QueryRow(ctx, fmt.Sprintf("SELECT count(*) FROM %s", pgIdent)).Scan(&count.SourceRows); err != nil {
		return count, fmt.Errorf("count source rows: %w", err)
	}

	colNames := make([]string, len(table.columns))
	placeholders := make([]string, len(table.columns))
	for i, col := range table.columns {
		colNames[i] = quoteSQLiteIdent(col.name)
		placeholders[i] = "?"
	}
	//nolint:gosec // Identifiers come from the compiled-in profile; values are bound.
	insertSQL := fmt.Sprintf(
		"INSERT INTO %s (%s) VALUES (%s)",
		quoteSQLiteIdent(table.name),
		strings.Join(colNames, ", "),
		strings.Join(placeholders, ", "),
	)
	stmt, err := sqliteTx.PrepareContext(ctx, insertSQL)
	if err != nil {
		return count, fmt.Errorf("prepare insert: %w", err)
	}
	defer func() { _ = stmt.Close() }()

	selectSQL := fmt.Sprintf("SELECT %s FROM %s ORDER BY id", strings.Join(pgColumnIdents(table.columns), ", "), pgIdent)
	rows, err := pgTx.Query(ctx, selectSQL)
	if err != nil {
		return count, fmt.Errorf("query source rows: %w", err)
	}
	defer rows.Close()

	args := make([]any, len(table.columns))
	for rows.Next() {
		if err := ctx.Err(); err != nil {
			return count, err
		}

		vals, err := rows.Values()
		if err != nil {
			return count, fmt.Errorf("read row values: %w", err)
		}
		if len(vals) != len(table.columns) {
			return count, fmt.Errorf("expected %d columns, got %d", len(table.columns), len(vals))
		}

		for i, col := range table.columns {
			converted, err := convertColumnValue(col, vals[i])
			if err != nil {
				return count, fmt.Errorf("column %s: %w", col.name, err)
			}
			args[i] = converted
		}

		if _, err := stmt.ExecContext(ctx, args...); err != nil {
			return count, fmt.Errorf("insert row: %w", err)
		}
		count.DestRows++
	}
	if err := rows.Err(); err != nil {
		return count, fmt.Errorf("iterate source rows: %w", err)
	}
	if count.DestRows != count.SourceRows {
		return count, fmt.Errorf("copied %d rows but source reported %d", count.DestRows, count.SourceRows)
	}

	return count, nil
}

func convertColumnValue(col postgresColumn, val any) (any, error) {
	if val == nil {
		return nil, nil //nolint:nilnil // SQL NULL is a successful conversion.
	}

	switch col.kind {
	case kindInt64:
		switch v := val.(type) {
		case int64:
			return v, nil
		case int32:
			return int64(v), nil
		case int16:
			return int64(v), nil
		default:
			return nil, fmt.Errorf("expected integer for kind %s, got %T", col.kind, val)
		}
	case kindText:
		if v, ok := val.(string); ok {
			return v, nil
		}
		return nil, fmt.Errorf("expected string for kind %s, got %T", col.kind, val)
	case kindBool:
		if v, ok := val.(bool); ok {
			if v {
				return int64(1), nil
			}
			return int64(0), nil
		}
		return nil, fmt.Errorf("expected bool for kind %s, got %T", col.kind, val)
	case kindTimestamp:
		if v, ok := val.(time.Time); ok {
			return v.UTC().Format(sqliteTimestampLayout), nil
		}
		return nil, fmt.Errorf("expected time.Time for kind %s, got %T", col.kind, val)
	default:
		return nil, fmt.Errorf("unknown column kind %v", col.kind)
	}
}

func pgColumnIdents(cols []postgresColumn) []string {
	idents := make([]string, len(cols))
	for i, col := range cols {
		idents[i] = pgx.Identifier{col.name}.Sanitize()
	}
	return idents
}

func quoteSQLiteIdent(name string) string {
	return fmt.Sprintf("%q", name)
}

func foreignKeyCheckSQLite(ctx context.Context, db *sql.DB) error {
	rows, err := db.QueryContext(ctx, "PRAGMA foreign_key_check")
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

func integrityCheckSQLite(ctx context.Context, db *sql.DB) error {
	var result string
	if err := db.QueryRowContext(ctx, "PRAGMA integrity_check").Scan(&result); err != nil {
		return fmt.Errorf("integrity check: %w", err)
	}
	if result != "ok" {
		return fmt.Errorf("integrity check failed: %s", result)
	}
	return nil
}
