package dbcore

import (
	"bytes"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestInitDatabase(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	var buf bytes.Buffer
	ctx := t.Context()

	if err := InitDatabase(ctx, db, &buf); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, "tables") {
		t.Errorf("expected summary with table count, got: %s", output)
	}

	// Verify tables were created.
	var tableCount int
	if err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount); err != nil {
		t.Fatalf("count tables: %v", err)
	}

	if tableCount < 100 {
		t.Errorf("expected 100+ tables, got %d", tableCount)
	}

	// Verify alembic_version has a value.
	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if ver == "" {
		t.Error("expected non-empty alembic version after init")
	}
	if ver != TargetVersion {
		t.Errorf("version = %q, want %q", ver, TargetVersion)
	}
	assertTagIndexes(t, db, true)
}

func TestApplyMigrations_TagIndexesRepairDuplicateActiveRows(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	if _, err := db.ExecContext(ctx, `DROP INDEX tag_repository_id_name_active`); err != nil {
		t.Fatalf("drop active index: %v", err)
	}
	if _, err := db.ExecContext(ctx, `DROP INDEX tag_repository_id_name_lifetime_end_ms`); err != nil {
		t.Fatalf("drop history index: %v", err)
	}
	if _, err := db.ExecContext(ctx,
		`CREATE UNIQUE INDEX tag_repository_id_name_lifetime_end_ms ON tag (repository_id, name, lifetime_end_ms)`,
	); err != nil {
		t.Fatalf("create old unique history index: %v", err)
	}
	if _, err := db.ExecContext(ctx, `UPDATE alembic_version SET version_num = ?`, BridgeTargetVersion); err != nil {
		t.Fatalf("stamp bridge version: %v", err)
	}

	insertTagMigrationFixture(t, db)

	var buf bytes.Buffer
	if err := ApplyMigrations(ctx, db, BridgeTargetVersion, TargetVersion, &buf); err != nil {
		t.Fatalf("ApplyMigrations: %v\n%s", err, buf.String())
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if ver != TargetVersion {
		t.Errorf("version = %q, want %q", ver, TargetVersion)
	}
	assertTagIndexes(t, db, true)

	var activeCount int
	if err := db.QueryRowContext(ctx,
		`SELECT count(*) FROM tag WHERE repository_id = 1 AND name = 'latest' AND lifetime_end_ms IS NULL`,
	).Scan(&activeCount); err != nil {
		t.Fatalf("count active tags: %v", err)
	}
	if activeCount != 1 {
		t.Fatalf("active tag count = %d, want 1", activeCount)
	}

	var activeManifestID int64
	if err := db.QueryRowContext(ctx,
		`SELECT manifest_id FROM tag WHERE repository_id = 1 AND name = 'latest' AND lifetime_end_ms IS NULL`,
	).Scan(&activeManifestID); err != nil {
		t.Fatalf("active manifest: %v", err)
	}
	if activeManifestID != 2 {
		t.Errorf("active manifest_id = %d, want 2", activeManifestID)
	}

	var expiredEnd, expiredStart int64
	if err := db.QueryRowContext(ctx,
		`SELECT lifetime_start_ms, lifetime_end_ms FROM tag WHERE id = 1`,
	).Scan(&expiredStart, &expiredEnd); err != nil {
		t.Fatalf("expired duplicate active row: %v", err)
	}
	if expiredEnd < expiredStart {
		t.Fatalf("expired row has invalid interval: start=%d end=%d", expiredStart, expiredEnd)
	}

	if _, err := db.ExecContext(ctx,
		`INSERT INTO tag (id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
		 VALUES (3, 'latest', 1, 1, 250, 300, 1),
		        (4, 'latest', 1, 2, 260, 300, 1)`,
	); err != nil {
		t.Fatalf("insert duplicate expired history: %v", err)
	}

	_, err = db.ExecContext(ctx,
		`INSERT INTO tag (id, name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
		 VALUES (5, 'latest', 1, 1, 400, 1)`,
	)
	if err == nil {
		t.Fatal("expected duplicate active tag insert to fail")
	}
}

func TestInitDatabase_RejectsExisting(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	ctx := t.Context()

	// First init should succeed.
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("first InitDatabase: %v", err)
	}

	// Second init should fail.
	err = InitDatabase(ctx, db, &bytes.Buffer{})
	if err == nil {
		t.Fatal("expected error on second init")
	}
	if !strings.Contains(err.Error(), "already contains") {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestSchemaVersion_EmptyDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "empty.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	ver, err := SchemaVersion(t.Context(), db)
	if err != nil {
		t.Fatalf("SchemaVersion on empty db: %v", err)
	}
	if ver != "" {
		t.Errorf("expected empty version for uninitialised db, got %q", ver)
	}
}

func TestSplitStatements_DropsLineCommentsWithoutDroppingStatements(t *testing.T) {
	migrationSQL := `-- migration metadata
-- section comment
CREATE TABLE first (id INTEGER);

-- next section
CREATE TABLE second (id INTEGER);
`

	stmts := splitStatements(migrationSQL)
	if len(stmts) != 2 {
		t.Fatalf("expected 2 statements, got %d: %#v", len(stmts), stmts)
	}
	if !strings.Contains(stmts[0], "CREATE TABLE first") {
		t.Errorf("first statement was dropped: %#v", stmts)
	}
	if !strings.Contains(stmts[1], "CREATE TABLE second") {
		t.Errorf("second statement was dropped: %#v", stmts)
	}
}

func TestIntegrityCheck(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	ctx := t.Context()
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	if err := IntegrityCheck(ctx, db); err != nil {
		t.Errorf("IntegrityCheck failed: %v", err)
	}
}

func TestBackupAndClean(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "test.db")

	// Create the file to back up.
	if err := os.WriteFile(dbPath, []byte("test"), 0o644); err != nil {
		t.Fatalf("write db: %v", err)
	}

	// Create 4 backups with distinct names (timestamps within the same second
	// would collide, so we create them manually).
	var paths []string
	for i := 0; i < 4; i++ {
		p := filepath.Join(dir, fmt.Sprintf("test.db.backup-2026010%dT120000Z", i))
		if err := os.WriteFile(p, []byte("backup"), 0o644); err != nil {
			t.Fatalf("write backup %d: %v", i, err)
		}
		paths = append(paths, p)
	}

	// Clean, keeping 2.
	if err := CleanOldBackups(dbPath, 2); err != nil {
		t.Fatalf("CleanOldBackups: %v", err)
	}

	// Oldest 2 should be gone, newest 2 should remain.
	for _, p := range paths[:2] {
		if _, err := os.Stat(p); !os.IsNotExist(err) {
			t.Errorf("expected %s to be deleted", p)
		}
	}
	for _, p := range paths[2:] {
		if _, err := os.Stat(p); err != nil {
			t.Errorf("expected %s to exist: %v", p, err)
		}
	}
}

func insertTagMigrationFixture(t *testing.T, db *sql.DB) {
	t.Helper()
	ctx := t.Context()
	statements := []string{
		`INSERT INTO "user" (
			id, username, email, verified, organization, robot, invoice_email,
			invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled
		) VALUES (1, 'library', 'library@example.com', 1, 0, 0, 0, 0, '2026-01-01 00:00:00', 1209600, 1)`,
		`INSERT INTO repository (
			id, namespace_user_id, name, visibility_id, description, badge_token, kind_id
		) VALUES (1, 1, 'nginx', 2, '', '', 1)`,
		`INSERT INTO manifest (id, repository_id, digest, media_type_id, manifest_bytes)
		 VALUES (1, 1, 'sha256:111', 17, '{}'),
		        (2, 1, 'sha256:222', 17, '{}')`,
		`INSERT INTO tag (id, name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
		 VALUES (1, 'latest', 1, 1, 100, 1),
		        (2, 'latest', 1, 2, 200, 1)`,
	}
	for _, stmt := range statements {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			t.Fatalf("insert fixture: %v\nstatement: %s", err, stmt)
		}
	}
}

func assertTagIndexes(t *testing.T, db *sql.DB, wantActiveUnique bool) {
	t.Helper()
	ctx := t.Context()

	var historySQL string
	if err := db.QueryRowContext(ctx,
		`SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'tag_repository_id_name_lifetime_end_ms'`,
	).Scan(&historySQL); err != nil {
		t.Fatalf("query history tag index: %v", err)
	}
	if strings.Contains(strings.ToUpper(historySQL), "UNIQUE") {
		t.Fatalf("history tag index should be non-unique: %s", historySQL)
	}

	var activeSQL string
	err := db.QueryRowContext(ctx,
		`SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'tag_repository_id_name_active'`,
	).Scan(&activeSQL)
	if !wantActiveUnique {
		if err != sql.ErrNoRows {
			t.Fatalf("active tag index should be absent, got sql=%q err=%v", activeSQL, err)
		}
		return
	}
	if err != nil {
		t.Fatalf("query active tag index: %v", err)
	}
	activeSQLUpper := strings.ToUpper(activeSQL)
	if !strings.Contains(activeSQLUpper, "UNIQUE") || !strings.Contains(activeSQLUpper, "WHERE LIFETIME_END_MS IS NULL") {
		t.Fatalf("active tag index should be unique and partial: %s", activeSQL)
	}
}
