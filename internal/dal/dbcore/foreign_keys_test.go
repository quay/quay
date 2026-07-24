package dbcore

import (
	"bytes"
	"context"
	"database/sql"
	"fmt"
	"strings"
	"testing"
)

const foreignKeyFixtureSchema = `
CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
CREATE TABLE parent (id INTEGER PRIMARY KEY);
CREATE TABLE child (
	id INTEGER PRIMARY KEY,
	parent_id INTEGER NOT NULL,
	FOREIGN KEY(parent_id) REFERENCES parent(id)
);
CREATE TABLE "user" (id INTEGER PRIMARY KEY, email TEXT NOT NULL, organization BOOLEAN NOT NULL);
CREATE TABLE organizationcontactemail (
	id INTEGER PRIMARY KEY,
	organization_id INTEGER NOT NULL,
	contact_email TEXT
);
CREATE TABLE oauthaccesstoken (id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL);
CREATE TABLE logentrykind (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);`

func TestInitDatabase_SeedForeignKeyViolationRollsBackAndRetries(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()
	catalog := testForeignKeyCatalog(t, "")
	invalidSeed := fmt.Sprintf(`
INSERT INTO alembic_version VALUES('%s');
INSERT INTO child (id, parent_id) VALUES (1, 999);`, TargetVersion)

	err := initDatabaseWithSources(
		t.Context(), db, catalog, foreignKeyFixtureSchema, invalidSeed, &bytes.Buffer{},
	)
	if err == nil || !strings.Contains(err.Error(), "foreign key violation") {
		t.Fatalf("error = %v, want transactional seed foreign-key failure", err)
	}
	assertForeignKeysEnabled(t, db)
	assertNoUserTables(t, db)

	validSeed := fmt.Sprintf(`
INSERT INTO alembic_version VALUES('%s');
INSERT INTO parent (id) VALUES (1);
INSERT INTO child (id, parent_id) VALUES (1, 1);`, TargetVersion)
	if err := initDatabaseWithSources(
		t.Context(), db, catalog, foreignKeyFixtureSchema, validSeed, &bytes.Buffer{},
	); err != nil {
		t.Fatalf("retry valid initialization: %v", err)
	}
	assertSchemaVersion(t, db, TargetVersion)
}

func TestInitDatabase_OrphaningMigrationRollsBackDataAndVersionAndRetries(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()
	failingCatalog := testForeignKeyCatalog(t,
		`INSERT INTO child (id, parent_id) VALUES (1, 999);`,
	)
	seedSQL := fmt.Sprintf(`
INSERT INTO alembic_version VALUES('%s');
INSERT INTO parent (id) VALUES (1);`, BridgeTargetVersion)

	err := initDatabaseWithSources(
		t.Context(), db, failingCatalog, foreignKeyFixtureSchema, seedSQL, &bytes.Buffer{},
	)
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "foreign key") {
		t.Fatalf("error = %v, want migration foreign-key failure", err)
	}
	assertForeignKeysEnabled(t, db)
	assertSchemaVersion(t, db, BridgeTargetVersion)
	assertChildRowCount(t, db, 0)

	retryCatalog := testForeignKeyCatalog(t,
		`INSERT INTO child (id, parent_id) VALUES (1, 1);`,
	)
	if err := applyMigrationsWithCatalog(
		t.Context(), db, retryCatalog, BridgeTargetVersion, TargetVersion, &bytes.Buffer{},
	); err != nil {
		t.Fatalf("retry valid migration: %v", err)
	}
	assertSchemaVersion(t, db, TargetVersion)
	assertChildRowCount(t, db, 1)
}

func TestBridgeForeignKeyViolationRollsBackDataAndVersionAndRetries(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()
	ctx := t.Context()
	if _, err := db.ExecContext(ctx, foreignKeyFixtureSchema); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx,
		`INSERT INTO alembic_version VALUES ('old_revision')`,
	); err != nil {
		t.Fatal(err)
	}

	bridgeRoot := migrationInfo{revision: BridgeTargetVersion}
	err := bridgeToRootWithApply(
		ctx, db, "old_revision", bridgeRoot, &bytes.Buffer{},
		func(ctx context.Context, tx *sql.Tx, _ string) error {
			_, err := tx.ExecContext(ctx,
				`INSERT INTO child (id, parent_id) VALUES (1, 999)`,
			)
			return err
		},
	)
	if err == nil || !strings.Contains(err.Error(), "foreign key violation") {
		t.Fatalf("error = %v, want bridge foreign-key failure", err)
	}
	assertForeignKeysEnabled(t, db)
	assertSchemaVersion(t, db, "old_revision")
	assertChildRowCount(t, db, 0)

	if err := bridgeToRootWithApply(
		ctx, db, "old_revision", bridgeRoot, &bytes.Buffer{},
		func(ctx context.Context, tx *sql.Tx, _ string) error {
			if _, err := tx.ExecContext(ctx, `INSERT INTO parent (id) VALUES (1)`); err != nil {
				return err
			}
			_, err := tx.ExecContext(ctx,
				`INSERT INTO child (id, parent_id) VALUES (1, 1)`,
			)
			return err
		},
	); err != nil {
		t.Fatalf("retry valid bridge: %v", err)
	}
	assertSchemaVersion(t, db, BridgeTargetVersion)
	assertChildRowCount(t, db, 1)
}

func testForeignKeyCatalog(t *testing.T, migrationBody string) *migrationCatalog {
	t.Helper()
	catalog, err := loadMigrationCatalog(testMigrationFS(map[string]string{
		"0001.sql": testMigrationSQL(BridgeTargetVersion, "", ""),
		"0002.sql": testMigrationSQL(TargetVersion, BridgeTargetVersion, migrationBody),
	}))
	if err != nil {
		t.Fatalf("load test migration catalog: %v", err)
	}
	return catalog
}

func assertForeignKeysEnabled(t *testing.T, db *sql.DB) {
	t.Helper()
	var enabled int
	if err := db.QueryRowContext(t.Context(), `PRAGMA foreign_keys`).Scan(&enabled); err != nil {
		t.Fatal(err)
	}
	if enabled != 1 {
		t.Errorf("foreign_keys = %d, want 1", enabled)
	}
}

func assertNoUserTables(t *testing.T, db *sql.DB) {
	t.Helper()
	var count int
	if err := db.QueryRowContext(t.Context(),
		`SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'`,
	).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Errorf("database retained %d table(s) after failed initialization", count)
	}
}

func assertChildRowCount(t *testing.T, db *sql.DB, want int) {
	t.Helper()
	var got int
	if err := db.QueryRowContext(t.Context(), `SELECT count(*) FROM child`).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Errorf("child row count = %d, want %d", got, want)
	}
}
