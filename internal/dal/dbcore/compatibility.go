package dbcore

import (
	"context"
	"database/sql"
	"fmt"
)

// ValidateSourceCompatibility checks a source database without changing it.
// Only the OMR v2.0.11 revision covered by the migration E2E is accepted.
func ValidateSourceCompatibility(ctx context.Context, db *sql.DB) error {
	rows, err := db.QueryContext(ctx, "SELECT version_num FROM alembic_version")
	if err != nil {
		return fmt.Errorf("read alembic_version: %w", err)
	}
	defer func() { _ = rows.Close() }()

	var revisions []string
	for rows.Next() {
		var revision string
		if err := rows.Scan(&revision); err != nil {
			return fmt.Errorf("scan alembic_version: %w", err)
		}
		revisions = append(revisions, revision)
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate alembic_version: %w", err)
	}
	if len(revisions) != 1 {
		return fmt.Errorf("source alembic_version must contain exactly one revision, found %d", len(revisions))
	}
	if revisions[0] != ApprovedOMRSourceVersion {
		return fmt.Errorf("unsupported OMR source revision %q; only %q is supported", revisions[0], ApprovedOMRSourceVersion)
	}

	if err := IntegrityCheck(ctx, db); err != nil {
		return fmt.Errorf("source database integrity check: %w", err)
	}
	if err := ForeignKeyCheck(ctx, db); err != nil {
		return fmt.Errorf("source database foreign key check: %w", err)
	}

	return nil
}

// ForeignKeyCheck reports the first SQLite foreign-key violation.
func ForeignKeyCheck(ctx context.Context, db *sql.DB) error {
	rows, err := db.QueryContext(ctx, "PRAGMA foreign_key_check")
	if err != nil {
		return err
	}
	defer func() { _ = rows.Close() }()

	if rows.Next() {
		var table, rowid, parent, fkid string
		if err := rows.Scan(&table, &rowid, &parent, &fkid); err != nil {
			return fmt.Errorf("scan violation: %w", err)
		}
		return fmt.Errorf("violation in %s row %s referencing %s", table, rowid, parent)
	}
	return rows.Err()
}
