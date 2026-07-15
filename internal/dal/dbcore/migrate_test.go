package dbcore

import (
	"bytes"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/quay/quay/internal/dal/schema"
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
	for _, expected := range []string{
		"Found 1 migration file(s)",
		"Applying: 0002_tag_active_unique_index.sql",
		"Migration complete: 1 migration(s) applied",
	} {
		if !strings.Contains(output, expected) {
			t.Errorf("initialization output missing %q:\n%s", expected, output)
		}
	}
	if strings.Contains(output, "0001_bridge_from_omr.sql") {
		t.Errorf("initialization unexpectedly applied the OMR bridge root:\n%s", output)
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
	assertTagIndexes(t, db)
}

func TestListMigrations_ReportsSupportedTwoFileChain(t *testing.T) {
	var output bytes.Buffer
	ListMigrations(&output)

	const expected = "Pending migrations:\n" +
		"  - 0001_bridge_from_omr.sql\n" +
		"  - 0002_tag_active_unique_index.sql\n"
	if output.String() != expected {
		t.Fatalf("ListMigrations output:\n%s\nwant:\n%s", output.String(), expected)
	}
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
	assertTagIndexes(t, db)

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

func TestApplyMigrations_NormalizesReferrerProtectionNames(t *testing.T) {
	db := prepareLegacyTagMigration(t)
	ctx := t.Context()

	sharedPrefix := strings.Repeat("a", 12)
	digest1 := "sha256:" + sharedPrefix + strings.Repeat("1", 52)
	digest2 := "sha256:" + sharedPrefix + strings.Repeat("2", 52)
	statements := []struct {
		query string
		args  []any
	}{
		{
			query: `INSERT INTO "user" (
				id, username, email, verified, organization, robot, invoice_email,
				invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled
			) VALUES (11, 'migration-referrers', 'migration-referrers@example.com', 1, 0, 0, 0, 0,
				'2026-01-01 00:00:00', 1209600, 1)`,
		},
		{
			query: `INSERT INTO repository (
				id, namespace_user_id, name, visibility_id, description, badge_token, kind_id
			) VALUES (11, 11, 'referrers', 2, '', '', 1)`,
		},
		{
			query: `INSERT INTO manifest (id, repository_id, digest, media_type_id, manifest_bytes)
				VALUES (101, 11, ?, 17, '{}'), (102, 11, ?, 17, '{}'),
				       (103, 11, 'malformed', 17, '{}')`,
			args: []any{digest1, digest2},
		},
		{
			query: `INSERT INTO tag (
				id, name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id, hidden
			) VALUES (101, '$referrer-aaaaaaaaaaaa', 11, 101, 100, 1, 1),
			         (102, '$referrer-aaaaaaaaaaaa', 11, 102, 200, 1, 1),
			         (103, '$referrer-aaaaaaaaaaaa', 11, 101, 300, 1, 1),
			         (104, '$referrer-broken', 11, 103, 400, 1, 1),
			         (105, '$referrer-broken', 11, NULL, 500, 1, 1)`,
		},
	}
	for _, stmt := range statements {
		if _, err := db.ExecContext(ctx, stmt.query, stmt.args...); err != nil {
			t.Fatalf("insert migration fixture: %v\nstatement: %s", err, stmt.query)
		}
	}

	if err := ApplyMigrations(ctx, db, BridgeTargetVersion, TargetVersion, &bytes.Buffer{}); err != nil {
		t.Fatalf("ApplyMigrations: %v", err)
	}

	assertActiveProtection := func(name string, manifestID sql.NullInt64) {
		t.Helper()
		var gotManifestID sql.NullInt64
		if err := db.QueryRowContext(ctx,
			`SELECT manifest_id FROM tag
			 WHERE repository_id = 11 AND name = ? AND hidden = 1 AND lifetime_end_ms IS NULL`,
			name,
		).Scan(&gotManifestID); err != nil {
			t.Fatalf("active protection %q: %v", name, err)
		}
		if gotManifestID != manifestID {
			t.Fatalf("active protection %q manifest = %v, want %v", name, gotManifestID, manifestID)
		}
	}
	assertActiveProtection("$referrer-sha256-"+sharedPrefix+strings.Repeat("1", 52), sql.NullInt64{Int64: 101, Valid: true})
	assertActiveProtection("$referrer-sha256-"+sharedPrefix+strings.Repeat("2", 52), sql.NullInt64{Int64: 102, Valid: true})
	assertActiveProtection("$referrer-$legacy-104", sql.NullInt64{Int64: 103, Valid: true})
	assertActiveProtection("$referrer-$legacy-105", sql.NullInt64{})

	var duplicateEnd int64
	if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = 101`).Scan(&duplicateEnd); err != nil {
		t.Fatalf("expired true retry duplicate: %v", err)
	}
	if duplicateEnd != 300 {
		t.Fatalf("retry duplicate lifetime_end_ms = %d, want 300", duplicateEnd)
	}
	var activeHidden int
	if err := db.QueryRowContext(ctx,
		`SELECT count(*) FROM tag WHERE repository_id = 11 AND hidden = 1 AND lifetime_end_ms IS NULL`,
	).Scan(&activeHidden); err != nil {
		t.Fatal(err)
	}
	if activeHidden != 4 {
		t.Fatalf("active hidden protection rows = %d, want 4", activeHidden)
	}
}

func TestApplyMigrations_RanksAllDuplicateActiveTagGroups(t *testing.T) {
	db := prepareLegacyTagMigration(t)
	ctx := t.Context()

	statements := []string{
		`INSERT INTO "user" (
			id, username, email, verified, organization, robot, invoice_email,
			invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled
		) VALUES (21, 'ranking-one', 'ranking-one@example.com', 1, 0, 0, 0, 0,
			'2026-01-01 00:00:00', 1209600, 1),
		         (22, 'ranking-two', 'ranking-two@example.com', 1, 0, 0, 0, 0,
			'2026-01-01 00:00:00', 1209600, 1)`,
		`INSERT INTO repository (
			id, namespace_user_id, name, visibility_id, description, badge_token, kind_id
		) VALUES (21, 21, 'one', 2, '', '', 1), (22, 22, 'two', 2, '', '', 1)`,
		`INSERT INTO manifest (id, repository_id, digest, media_type_id, manifest_bytes)
		 VALUES (201, 21, 'sha256:201', 17, '{}'), (202, 21, 'sha256:202', 17, '{}'),
		        (203, 22, 'sha256:203', 17, '{}'), (204, 22, 'sha256:204', 17, '{}')`,
		`INSERT INTO tag (id, name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id)
		 VALUES (201, 'latest', 21, 201, 100, 1),
		        (202, 'latest', 21, 202, 200, 1),
		        (203, 'latest', 21, 201, 200, 1),
		        (204, 'stable', 21, 201, 10, 1),
		        (205, 'stable', 21, 202, 20, 1),
		        (206, 'latest', 22, 203, 500, 1),
		        (207, 'latest', 22, 204, 400, 1),
		        (208, 'latest', 22, 204, 500, 1)`,
	}
	for _, stmt := range statements {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			t.Fatalf("insert ranking fixture: %v\nstatement: %s", err, stmt)
		}
	}

	if err := ApplyMigrations(ctx, db, BridgeTargetVersion, TargetVersion, &bytes.Buffer{}); err != nil {
		t.Fatalf("ApplyMigrations: %v", err)
	}

	wantEnds := map[int64]sql.NullInt64{
		201: {Int64: 200, Valid: true},
		202: {Int64: 200, Valid: true},
		203: {},
		204: {Int64: 20, Valid: true},
		205: {},
		206: {Int64: 500, Valid: true},
		207: {Int64: 500, Valid: true},
		208: {},
	}
	for id, wantEnd := range wantEnds {
		var gotEnd sql.NullInt64
		if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = ?`, id).Scan(&gotEnd); err != nil {
			t.Fatalf("tag %d lifetime_end_ms: %v", id, err)
		}
		if gotEnd != wantEnd {
			t.Errorf("tag %d lifetime_end_ms = %v, want %v", id, gotEnd, wantEnd)
		}
	}
}

func TestInitDatabase_ContainsOAuthAPITokenMetadata(t *testing.T) {
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

	for _, column := range []string{oauthCreatedColumn, oauthLastAccessedColumn} {
		var count int
		err := db.QueryRowContext(ctx,
			"SELECT count(*) FROM pragma_table_info('oauthaccesstoken') WHERE name=?", column,
		).Scan(&count)
		if err != nil {
			t.Fatalf("query column %s: %v", column, err)
		}
		if count != 1 {
			t.Errorf("expected oauthaccesstoken.%s to exist", column)
		}
	}

	var indexedColumns string
	err = db.QueryRowContext(ctx,
		"SELECT group_concat(name, ',') FROM (SELECT name FROM pragma_index_info('oauthaccesstoken_application_id_last_accessed') ORDER BY seqno)",
	).Scan(&indexedColumns)
	if err != nil {
		t.Fatalf("query oauth access token last_accessed index: %v", err)
	}
	if indexedColumns != "application_id,last_accessed" {
		t.Errorf("expected oauth access token last_accessed index columns application_id,last_accessed; got %s", indexedColumns)
	}

	for _, kind := range []string{createOAuthAPILogKind, revokeOAuthAPILogKind} {
		var count int
		err := db.QueryRowContext(ctx,
			"SELECT count(*) FROM logentrykind WHERE name=?", kind,
		).Scan(&count)
		if err != nil {
			t.Fatalf("query log kind %s: %v", kind, err)
		}
		if count != 1 {
			t.Errorf("expected log kind %s to exist", kind)
		}
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

func TestLoadMigrationCatalog_RejectsInvalidGraphs(t *testing.T) {
	tests := []struct {
		name    string
		files   map[string]string
		wantErr string
	}{
		{
			name: "duplicate revisions",
			files: map[string]string{
				"0001.sql": testMigrationSQL("root", "", ""),
				"0002.sql": testMigrationSQL("root", "parent", ""),
			},
			wantErr: "duplicate revision",
		},
		{
			name: "duplicate down revisions",
			files: map[string]string{
				"0001.sql": testMigrationSQL("root", "", ""),
				"0002.sql": testMigrationSQL("one", "root", ""),
				"0003.sql": testMigrationSQL("two", "root", ""),
			},
			wantErr: "duplicate down_revision",
		},
		{
			name: "self link",
			files: map[string]string{
				"0001.sql": testMigrationSQL("root", "", ""),
				"0002.sql": testMigrationSQL("self", "self", ""),
			},
			wantErr: "self-link",
		},
		{
			name: "cycle",
			files: map[string]string{
				"0001.sql": testMigrationSQL("root", "", ""),
				"0002.sql": testMigrationSQL("one", "two", ""),
				"0003.sql": testMigrationSQL("two", "one", ""),
			},
			wantErr: "cycle",
		},
		{
			name: "dangling parent",
			files: map[string]string{
				"0001.sql": testMigrationSQL("root", "", ""),
				"0002.sql": testMigrationSQL("orphan", "missing", ""),
			},
			wantErr: "dangling down_revision",
		},
		{
			name: "missing bridge root",
			files: map[string]string{
				"0001.sql": testMigrationSQL("one", "missing", ""),
			},
			wantErr: "exactly one bridge root",
		},
		{
			name: "disconnected off-chain root",
			files: map[string]string{
				"0001.sql": testMigrationSQL("root-one", "", ""),
				"0002.sql": testMigrationSQL("one", "root-one", ""),
				"0003.sql": testMigrationSQL("root-two", "", ""),
				"0004.sql": testMigrationSQL("two", "root-two", ""),
			},
			wantErr: "exactly one bridge root",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := loadMigrationCatalog(testMigrationFS(tt.files))
			if err == nil {
				t.Fatal("expected invalid migration catalog to fail")
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("error = %q, want substring %q", err, tt.wantErr)
			}
		})
	}
}

func TestMigrationCatalog_RejectsSuccessorAfterTargetVersion(t *testing.T) {
	catalog, err := loadMigrationCatalog(testMigrationFS(map[string]string{
		"0001.sql": testMigrationSQL(BridgeTargetVersion, "", ""),
		"0002.sql": testMigrationSQL(TargetVersion, BridgeTargetVersion, ""),
		"0003.sql": testMigrationSQL("unexpected_successor", TargetVersion, ""),
	}))
	if err != nil {
		t.Fatalf("load migration catalog: %v", err)
	}
	if err := catalog.validateVersions(); err == nil || !strings.Contains(err.Error(), "terminal revision") {
		t.Fatalf("error = %v, want terminal revision mismatch", err)
	}
}

func TestApplyMigrations_UnreachableTargetDoesNotMutateDatabase(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()

	ctx := t.Context()
	if _, err := db.ExecContext(ctx, `CREATE TABLE alembic_version (version_num TEXT NOT NULL)`); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, `INSERT INTO alembic_version VALUES ('one')`); err != nil {
		t.Fatal(err)
	}

	fsys := testMigrationFS(map[string]string{
		"0001.sql": testMigrationSQL("root", "", ""),
		"0002.sql": testMigrationSQL("one", "root", "CREATE TABLE already_applied (id INTEGER);"),
		"0003.sql": testMigrationSQL("head", "one", "CREATE TABLE must_not_exist (id INTEGER);"),
	})
	err := applyMigrationsWithFS(ctx, db, fsys, "one", "root", &bytes.Buffer{})
	if err == nil || !strings.Contains(err.Error(), "unreachable") {
		t.Fatalf("error = %v, want unreachable target error", err)
	}

	version, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if version != "one" {
		t.Fatalf("version = %q, want one", version)
	}
	var tableCount int
	if err := db.QueryRowContext(ctx,
		`SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'must_not_exist'`,
	).Scan(&tableCount); err != nil {
		t.Fatal(err)
	}
	if tableCount != 0 {
		t.Fatal("migration SQL committed before the complete path was planned")
	}
}

func TestEmbeddedSeedVersionHasMigrationRoute(t *testing.T) {
	catalog, err := loadEmbeddedMigrationCatalog()
	if err != nil {
		t.Fatalf("load embedded migration catalog: %v", err)
	}
	if len(catalog.migrations) != 2 {
		t.Fatalf("embedded migration count = %d, want 2", len(catalog.migrations))
	}
	if catalog.chainableCount() != 1 {
		t.Fatalf("chainable migration count = %d, want 1", catalog.chainableCount())
	}
	if catalog.root.filename != "0001_bridge_from_omr.sql" || catalog.root.revision != BridgeTargetVersion {
		t.Fatalf("bridge root = %s (%s), want 0001_bridge_from_omr.sql (%s)",
			catalog.root.filename, catalog.root.revision, BridgeTargetVersion)
	}

	db := openTestDB(t)
	defer db.Close()
	ctx := t.Context()
	if _, err := db.ExecContext(ctx, `CREATE TABLE alembic_version (version_num TEXT NOT NULL)`); err != nil {
		t.Fatal(err)
	}
	for _, stmt := range splitStatements(schema.SeedDataSQL) {
		if strings.HasPrefix(stmt, "INSERT INTO alembic_version") {
			if _, err := db.ExecContext(ctx, stmt); err != nil {
				t.Fatalf("execute embedded version seed: %v", err)
			}
			break
		}
	}
	seedVersion, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if seedVersion == "" {
		t.Fatal("embedded seed data did not provide a schema version")
	}
	plan, err := catalog.plan(seedVersion, TargetVersion)
	if err != nil {
		t.Fatalf("embedded seed version %q has no route to %q: %v", seedVersion, TargetVersion, err)
	}
	if len(plan) != 1 || plan[0].filename != "0002_tag_active_unique_index.sql" {
		t.Fatalf("embedded seed route = %#v, want only 0002_tag_active_unique_index.sql", plan)
	}
}

func TestInitDatabase_MigrationFailureRestoresForeignKeysAndLeavesSeedVersionRetryable(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()
	ctx := t.Context()

	failingFS := testMigrationFS(map[string]string{
		"0001.sql": testMigrationSQL(BridgeTargetVersion, "", ""),
		"0002.sql": testMigrationSQL(
			TargetVersion,
			BridgeTargetVersion,
			"CREATE TABLE recovered (id INTEGER); CREATE TABLE broken (",
		),
	})
	err := initDatabaseWithFS(ctx, db, failingFS, &bytes.Buffer{})
	if err == nil || !strings.Contains(err.Error(), "apply Go-only migrations") {
		t.Fatalf("error = %v, want migration failure", err)
	}

	var foreignKeys int
	if err := db.QueryRowContext(ctx, "PRAGMA foreign_keys").Scan(&foreignKeys); err != nil {
		t.Fatal(err)
	}
	if foreignKeys != 1 {
		t.Fatalf("foreign_keys = %d, want 1", foreignKeys)
	}
	seedVersion, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	if seedVersion != BridgeTargetVersion {
		t.Fatalf("version = %q, want retryable seed version %q", seedVersion, BridgeTargetVersion)
	}

	retryFS := testMigrationFS(map[string]string{
		"0001.sql": testMigrationSQL(BridgeTargetVersion, "", ""),
		"0002.sql": testMigrationSQL(TargetVersion, BridgeTargetVersion, "CREATE TABLE recovered (id INTEGER);"),
	})
	if err := applyMigrationsWithFS(
		ctx, db, retryFS, seedVersion, TargetVersion, &bytes.Buffer{},
	); err != nil {
		t.Fatalf("retry migration from seeded version: %v", err)
	}
}

func TestInitDatabase_InvalidSeedRouteDoesNotCommitSchema(t *testing.T) {
	versionSeed := fmt.Sprintf("INSERT INTO alembic_version VALUES('%s');", BridgeTargetVersion)
	tests := []struct {
		name    string
		seedSQL string
		wantErr string
	}{
		{
			name:    "missing version marker",
			seedSQL: strings.Replace(schema.SeedDataSQL, versionSeed, "", 1),
			wantErr: "read seeded schema version",
		},
		{
			name: "unreachable version marker",
			seedSQL: strings.Replace(
				schema.SeedDataSQL,
				versionSeed,
				"INSERT INTO alembic_version VALUES('unreachable_seed');",
				1,
			),
			wantErr: "plan Go-only migrations",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			db := openTestDB(t)
			defer db.Close()
			ctx := t.Context()
			catalog, err := loadEmbeddedMigrationCatalog()
			if err != nil {
				t.Fatal(err)
			}

			err = initDatabaseWithSources(
				ctx, db, catalog, schema.QuaySchemaSQL, tt.seedSQL, &bytes.Buffer{},
			)
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("error = %v, want substring %q", err, tt.wantErr)
			}

			var tableCount int
			if err := db.QueryRowContext(ctx,
				"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
			).Scan(&tableCount); err != nil {
				t.Fatal(err)
			}
			if tableCount != 0 {
				t.Fatalf("schema transaction committed %d tables after seed route failure", tableCount)
			}
			var foreignKeys int
			if err := db.QueryRowContext(ctx, "PRAGMA foreign_keys").Scan(&foreignKeys); err != nil {
				t.Fatal(err)
			}
			if foreignKeys != 1 {
				t.Fatalf("foreign_keys = %d, want 1", foreignKeys)
			}
			if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
				t.Fatalf("retry InitDatabase after seed route failure: %v", err)
			}
		})
	}
}

func TestInitDatabase_InvalidCatalogDoesNotCommitSchema(t *testing.T) {
	db := openTestDB(t)
	defer db.Close()
	ctx := t.Context()

	invalidFS := testMigrationFS(map[string]string{
		"0001.sql": testMigrationSQL(BridgeTargetVersion, "", ""),
		"0002.sql": testMigrationSQL(TargetVersion, "missing_parent", ""),
	})
	err := initDatabaseWithFS(ctx, db, invalidFS, &bytes.Buffer{})
	if err == nil || !strings.Contains(err.Error(), "dangling down_revision") {
		t.Fatalf("error = %v, want dangling catalog error", err)
	}

	var tableCount int
	if err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount); err != nil {
		t.Fatal(err)
	}
	if tableCount != 0 {
		t.Fatalf("invalid catalog committed %d tables", tableCount)
	}
}

func testMigrationFS(files map[string]string) fstest.MapFS {
	fsys := make(fstest.MapFS, len(files))
	for name, contents := range files {
		fsys[name] = &fstest.MapFile{Data: []byte(contents)}
	}
	return fsys
}

func testMigrationSQL(revision, downRevision, body string) string {
	var migration strings.Builder
	fmt.Fprintf(&migration, "-- revision: %s\n", revision)
	if downRevision != "" {
		fmt.Fprintf(&migration, "-- down_revision: %s\n", downRevision)
	}
	migration.WriteString(body)
	return migration.String()
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

func prepareLegacyTagMigration(t *testing.T) *sql.DB {
	t.Helper()
	db := openTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	ctx := t.Context()
	if err := InitDatabase(ctx, db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	for _, stmt := range []string{
		`DROP INDEX tag_repository_id_name_active`,
		`DROP INDEX tag_repository_id_name_lifetime_end_ms`,
		`CREATE UNIQUE INDEX tag_repository_id_name_lifetime_end_ms
		 ON tag (repository_id, name, lifetime_end_ms)`,
	} {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			t.Fatalf("prepare legacy tag indexes: %v\nstatement: %s", err, stmt)
		}
	}
	if _, err := db.ExecContext(ctx,
		`UPDATE alembic_version SET version_num = ?`, BridgeTargetVersion,
	); err != nil {
		t.Fatalf("stamp bridge version: %v", err)
	}
	return db
}

func assertTagIndexes(t *testing.T, db *sql.DB) {
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
	if err := db.QueryRowContext(ctx,
		`SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'tag_repository_id_name_active'`,
	).Scan(&activeSQL); err != nil {
		t.Fatalf("query active tag index: %v", err)
	}
	activeSQLUpper := strings.ToUpper(activeSQL)
	if !strings.Contains(activeSQLUpper, "UNIQUE") || !strings.Contains(activeSQLUpper, "WHERE LIFETIME_END_MS IS NULL") {
		t.Fatalf("active tag index should be unique and partial: %s", activeSQL)
	}
}
