// Integration tests require QUAY_TEST_POSTGRES_DSN. `make go-test-postgres`
// provides a disposable PostgreSQL 16 server.
package postgres

import (
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5"

	"github.com/quay/quay/internal/dal/dbcore"
)

const (
	postgresDSNEnv              = "QUAY_TEST_POSTGRES_DSN"
	postgresAllowDestructiveEnv = "QUAY_TEST_POSTGRES_ALLOW_DESTRUCTIVE"
	postgresTestDatabase        = "quay_migrate_test"
)

const postgresDataDML = `
INSERT INTO "user" (id, uuid, username, password_hash, email, verified, stripe_id, organization, robot, invoice_email, invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled, invoice_email_address, company, family_name, given_name, location, maximum_queued_builds_count, creation_date, last_accessed) VALUES
	(1, 'c6f515bd-b3fa-4c00-9e50-699d713a7ea5', 'init', 'FIXTURE-NOT-A-REAL-HASH', 'init@quay.io', true, NULL, false, false, false, 0, '2026-07-31 12:36:42.332282', 1209600, true, NULL, 'Acme Corp', 'Init', 'User', 'Raleigh', 4, '2026-07-31 12:36:42.332287', '2026-07-31 13:00:00'),
	(2, NULL, 'init+robot', NULL, 'init+robot@quay.io', false, NULL, false, true, false, 0, '2026-07-31 12:36:42', 1209600, true, NULL, NULL, NULL, NULL, NULL, NULL, '2026-07-31 12:40:00', NULL);

INSERT INTO repository (id, namespace_user_id, name, visibility_id, description, badge_token, kind_id, trust_enabled, state) VALUES
	(1, 1, 'test-image', 2, NULL, '989d65e7-6bad-4a2e-aeee-6e2a9290e704', 1, false, 0),
	(2, 1, 'documented', 2, 'has a description with ''quotes'' and text', 'b75362e4-d34e-41ef-ba08-958e71c0ab76', 1, true, 0);

INSERT INTO manifest (id, repository_id, digest, media_type_id, manifest_bytes, config_media_type, layers_compressed_size, subject, subject_backfilled, artifact_type, artifact_type_backfilled) VALUES
	(1, 1, 'sha256:4700df8bfea963e4339efd2990cfe3dc94647417cfdc9db8ffbed024e66cd1a2', 16, '{"schemaVersion":2,"mediaType":"application/vnd.docker.distribution.manifest.v2+json","config":{"mediaType":"application/vnd.docker.container.image.v1+json","size":4877,"digest":"sha256:e1cc75ec636fa7d9b8f2ac3f833fb00ae8f7ebd19f3c1989396efa91f78735fc"},"layers":[{"mediaType":"application/vnd.docker.image.rootfs.diff.tar.gzip","size":7255415,"digest":"sha256:e34240319f3ec71fce6b038cdef069885ea714c00b08b8e166ca3f5511eac601"}]}', 'application/vnd.docker.container.image.v1+json', 7255415, NULL, true, NULL, true),
	(2, 2, 'sha256:9f2a1b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e7f8', 16, '{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json","layers":[]}', 'application/vnd.oci.image.config.v1+json', 0, 'sha256:e34240319f3ec71fce6b038cdef069885ea714c00b08b8e166ca3f5511eac601', false, 'application/vnd.example.artifact', false);

INSERT INTO tag (id, name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, hidden, reversion, tag_kind_id, linked_tag_id) VALUES
	(1, 'v1', 1, 1, 1785501535630, NULL, false, false, 1, NULL),
	(2, 'v0', 2, 2, 1785501400000, 1785501500000, false, false, 1, NULL),
	(3, 'v1', 2, 2, 1785501536457, NULL, true, true, 1, 1);
`

func connectTestPostgres(t *testing.T) *pgx.Conn {
	t.Helper()
	dsn := os.Getenv(postgresDSNEnv)
	if dsn == "" {
		t.Skipf("skipping: set %s to a reachable PostgreSQL 16 connection string (see `make go-test-postgres`)", postgresDSNEnv)
	}

	config, err := pgx.ParseConfig(dsn)
	if err != nil {
		t.Fatalf("parse test postgres configuration from %s: %v", postgresDSNEnv, err)
	}
	if config.Database != postgresTestDatabase && os.Getenv(postgresAllowDestructiveEnv) != "1" {
		t.Fatalf(
			"refusing to reset PostgreSQL database %q: use a disposable database named %q or set %s=1",
			config.Database, postgresTestDatabase, postgresAllowDestructiveEnv,
		)
	}
	conn, err := pgx.ConnectConfig(t.Context(), config)
	if err != nil {
		t.Fatalf("connect to test postgres (%s): %v", postgresDSNEnv, err)
	}
	t.Cleanup(func() { _ = conn.Close(context.Background()) })

	if _, err := conn.Exec(t.Context(), `DROP SCHEMA public CASCADE; CREATE SCHEMA public`); err != nil {
		t.Fatalf("reset postgres schema: %v", err)
	}
	schemaSQL := mustReadFixture(t, "omr_v2.0.11_postgres_3f8d7acdf7f9_schema.sql")
	if _, err := conn.Exec(t.Context(), schemaSQL); err != nil {
		t.Fatalf("load real postgres schema fixture: %v", err)
	}
	if _, err := conn.Exec(t.Context(), `SET search_path = public`); err != nil {
		t.Fatalf("set fixture search path: %v", err)
	}
	loadCopyFixture(t, conn, mustReadFixture(t, "omr_v2.0.11_postgres_3f8d7acdf7f9_enum_seed_data.sql"))
	if _, err := conn.Exec(t.Context(), `INSERT INTO alembic_version (version_num) VALUES ($1)`, approvedPostgresProfile.SchemaRevision); err != nil {
		t.Fatalf("seed alembic revision: %v", err)
	}
	if _, err := conn.Exec(t.Context(), postgresDataDML); err != nil {
		t.Fatalf("seed representative postgres data: %v", err)
	}
	return conn
}

func mustReadFixture(t *testing.T, name string) string {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("..", "testdata", name))
	if err != nil {
		t.Fatalf("read fixture %s: %v", name, err)
	}
	return string(raw)
}

func loadCopyFixture(t *testing.T, conn *pgx.Conn, fixture string) {
	t.Helper()
	profileByTable := make(map[string]postgresTable, len(approvedPostgresProfile.Tables))
	for _, table := range approvedPostgresProfile.Tables {
		profileByTable[table.Name] = table
	}

	lines := strings.Split(fixture, "\n")
	for lineIndex := 0; lineIndex < len(lines); lineIndex++ {
		header := lines[lineIndex]
		if !strings.HasPrefix(header, "COPY public.") {
			continue
		}
		tableEnd := strings.Index(header, " (")
		columnsEnd := strings.LastIndex(header, ") FROM stdin;")
		if tableEnd < 0 || columnsEnd < tableEnd {
			t.Fatalf("parse COPY header %q", header)
		}
		tableName := strings.TrimPrefix(header[:tableEnd], "COPY public.")
		columnNames := strings.Split(header[tableEnd+2:columnsEnd], ", ")
		table, ok := profileByTable[tableName]
		if !ok {
			t.Fatalf("COPY fixture table %q is not in the frozen profile", tableName)
		}
		kindByColumn := make(map[string]columnKind, len(table.Columns))
		for _, column := range table.Columns {
			kindByColumn[column.Name] = column.Kind
		}

		var copyRows [][]any
		for lineIndex++; lineIndex < len(lines) && lines[lineIndex] != `\.`; lineIndex++ {
			rawValues := strings.Split(lines[lineIndex], "\t")
			if len(rawValues) != len(columnNames) {
				t.Fatalf("COPY fixture %s row has %d values, want %d", tableName, len(rawValues), len(columnNames))
			}
			row := make([]any, len(rawValues))
			for i, raw := range rawValues {
				row[i] = copyFixtureValue(t, tableName, columnNames[i], kindByColumn[columnNames[i]], raw)
			}
			copyRows = append(copyRows, row)
		}
		if lineIndex == len(lines) {
			t.Fatalf("COPY fixture %s has no terminator", tableName)
		}
		if _, err := conn.CopyFrom(t.Context(), pgx.Identifier{"public", tableName}, columnNames, pgx.CopyFromRows(copyRows)); err != nil {
			t.Fatalf("load COPY fixture table %s: %v", tableName, err)
		}
	}
}

func copyFixtureValue(t *testing.T, table, column string, kind columnKind, raw string) any {
	t.Helper()
	if raw == `\N` {
		return nil
	}
	if strings.Contains(raw, `\`) {
		t.Fatalf("unsupported COPY escape in %s.%s", table, column)
	}
	switch kind {
	case kindInt64:
		value, err := strconv.ParseInt(raw, 10, 64)
		if err != nil {
			t.Fatalf("parse fixture integer %s.%s: %v", table, column, err)
		}
		return value
	case kindBool:
		value, err := strconv.ParseBool(raw)
		if err != nil {
			t.Fatalf("parse fixture boolean %s.%s: %v", table, column, err)
		}
		return value
	case kindText:
		return raw
	default:
		t.Fatalf("unsupported COPY fixture kind %q for %s.%s", kind, table, column)
		return nil
	}
}

func newIntermediate(t *testing.T) *sql.DB {
	t.Helper()
	db, err := dbcore.OpenSQLite(filepath.Join(t.TempDir(), "quay.db.partial"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })
	if err := dbcore.InitOMRSourceIntermediate(t.Context(), db); err != nil {
		t.Fatalf("InitOMRSourceIntermediate: %v", err)
	}
	return db
}

func TestCopyPostgresToSQLite_Integration(t *testing.T) {
	conn := connectTestPostgres(t)
	sqliteDB := newIntermediate(t)

	report, err := CopyPostgresToSQLite(t.Context(), conn, sqliteDB)
	if err != nil {
		t.Fatalf("CopyPostgresToSQLite: %v", err)
	}
	if want := len(approvedPostgresProfile.Tables); len(report.Tables) != want {
		t.Fatalf("report table count = %d, want %d", len(report.Tables), want)
	}
	for table, count := range report.Tables {
		if count.SourceRows != count.DestRows {
			t.Errorf("table %s: source=%d dest=%d", table, count.SourceRows, count.DestRows)
		}
	}

	wantCounts := map[string]int64{
		"mediatype": 18, "visibility": 2, "imagestoragelocation": 8, "logentrykind": 114,
		"user": 2, "repository": 2, "manifest": 2, "tag": 3,
	}
	for table, want := range wantCounts {
		got := report.Tables[table]
		if got.SourceRows != want || got.DestRows != want {
			t.Errorf("table %s: source=%d dest=%d, want %d", table, got.SourceRows, got.DestRows, want)
		}
	}

	var mediatype15Name string
	mustScan(t, sqliteDB, `SELECT name FROM mediatype WHERE id = 15`, &mediatype15Name)
	const wantMediatype15 = "application/vnd.docker.distribution.manifest.v2+json"
	if mediatype15Name != wantMediatype15 {
		t.Errorf("mediatype 15 name = %q, want source-owned %q", mediatype15Name, wantMediatype15)
	}

	var verified, robot, enabled int64
	mustScan(t, sqliteDB, `SELECT verified, robot, enabled FROM "user" WHERE id = 1`, &verified, &robot, &enabled)
	if verified != 1 || robot != 0 || enabled != 1 {
		t.Errorf("user 1 booleans = verified=%d robot=%d enabled=%d, want 1,0,1", verified, robot, enabled)
	}

	var stripeID, company sql.NullString
	mustScan(t, sqliteDB, `SELECT stripe_id, company FROM "user" WHERE id = 2`, &stripeID, &company)
	if stripeID.Valid || company.Valid {
		t.Errorf("user 2 expected NULL stripe_id/company, got %+v %+v", stripeID, company)
	}

	var repo2Desc string
	var trustEnabled int64
	mustScan(t, sqliteDB, `SELECT description, trust_enabled FROM repository WHERE id = 2`, &repo2Desc, &trustEnabled)
	const wantDesc = "has a description with 'quotes' and text"
	if repo2Desc != wantDesc || trustEnabled != 1 {
		t.Errorf("repository 2 = description=%q trust_enabled=%d, want %q,1", repo2Desc, trustEnabled, wantDesc)
	}

	var manifestBytes string
	mustScan(t, sqliteDB, `SELECT manifest_bytes FROM manifest WHERE id = 2`, &manifestBytes)
	const wantManifestBytes = `{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json","layers":[]}`
	if manifestBytes != wantManifestBytes {
		t.Errorf("manifest 2 manifest_bytes = %q, want byte-identical %q", manifestBytes, wantManifestBytes)
	}

	var hidden, reversion int64
	var linkedTagID, lifetimeEnd sql.NullInt64
	mustScan(t, sqliteDB, `SELECT hidden, reversion, linked_tag_id, lifetime_end_ms FROM tag WHERE id = 3`, &hidden, &reversion, &linkedTagID, &lifetimeEnd)
	if hidden != 1 || reversion != 1 || !linkedTagID.Valid || linkedTagID.Int64 != 1 || lifetimeEnd.Valid {
		t.Errorf("tag 3 = hidden=%d reversion=%d linked_tag_id=%+v lifetime_end_ms=%+v", hidden, reversion, linkedTagID, lifetimeEnd)
	}

	if err := dbcore.ValidateSourceCompatibility(t.Context(), sqliteDB); err != nil {
		t.Fatalf("ValidateSourceCompatibility on copied intermediate: %v", err)
	}
	if err := dbcore.RunBridge(t.Context(), sqliteDB); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}
	version, err := dbcore.SchemaVersion(t.Context(), sqliteDB)
	if err != nil {
		t.Fatalf("SchemaVersion after bridge: %v", err)
	}
	if version != dbcore.TargetVersion {
		t.Fatalf("post-bridge version = %q, want %q", version, dbcore.TargetVersion)
	}
	if err := dbcore.IntegrityCheck(t.Context(), sqliteDB); err != nil {
		t.Errorf("post-bridge IntegrityCheck: %v", err)
	}

	result, err := sqliteDB.ExecContext(t.Context(),
		`INSERT INTO repository (namespace_user_id, name, visibility_id, badge_token) VALUES (?, ?, ?, ?)`,
		1, "post-migration-repo", 2, "post-migration-badge-token",
	)
	if err != nil {
		t.Fatalf("post-migration insert: %v", err)
	}
	newID, err := result.LastInsertId()
	if err != nil {
		t.Fatalf("LastInsertId: %v", err)
	}
	if newID <= 2 {
		t.Errorf("post-migration repository id = %d, want > 2", newID)
	}
}

func TestCopyPostgresToSQLite_Integration_RejectsDuplicateKey(t *testing.T) {
	conn := connectTestPostgres(t)
	sqliteDB := newIntermediate(t)

	if _, err := sqliteDB.ExecContext(t.Context(), `INSERT INTO "user" (id, username, email, verified, organization, robot, invoice_email, last_invalid_login, removed_tag_expiration_s) VALUES (1, 'preexisting', 'preexisting@quay.io', 0, 0, 0, 0, '2026-01-01 00:00:00', 1209600)`); err != nil {
		t.Fatalf("seed colliding destination row: %v", err)
	}

	if _, err := CopyPostgresToSQLite(t.Context(), conn, sqliteDB); err == nil {
		t.Fatal("CopyPostgresToSQLite unexpectedly succeeded against a colliding destination row")
	}
	var userCount, mediaTypeCount int
	mustScan(t, sqliteDB, `SELECT count(*) FROM "user"`, &userCount)
	mustScan(t, sqliteDB, `SELECT count(*) FROM mediatype`, &mediaTypeCount)
	if userCount != 1 || mediaTypeCount != 0 {
		t.Errorf("aborted copy was not rolled back: user=%d mediatype=%d", userCount, mediaTypeCount)
	}
}

func TestCopyPostgresToSQLite_Integration_RejectsNonEmptyDestination(t *testing.T) {
	conn := connectTestPostgres(t)
	sqliteDB := newIntermediate(t)

	if _, err := sqliteDB.ExecContext(t.Context(), `INSERT INTO quayregion (id, name) VALUES (99, 'preexisting')`); err != nil {
		t.Fatalf("seed non-colliding destination row: %v", err)
	}
	if _, err := CopyPostgresToSQLite(t.Context(), conn, sqliteDB); err == nil {
		t.Fatal("CopyPostgresToSQLite unexpectedly accepted a non-empty destination")
	}

	var regionCount, mediaTypeCount int
	mustScan(t, sqliteDB, `SELECT count(*) FROM quayregion`, &regionCount)
	mustScan(t, sqliteDB, `SELECT count(*) FROM mediatype`, &mediaTypeCount)
	if regionCount != 1 || mediaTypeCount != 0 {
		t.Errorf("aborted copy was not rolled back: quayregion=%d mediatype=%d", regionCount, mediaTypeCount)
	}
}

func TestCopyPostgresToSQLite_Integration_RejectsSourceDrift(t *testing.T) {
	t.Run("revision", func(t *testing.T) {
		conn := connectTestPostgres(t)
		if _, err := conn.Exec(t.Context(), `UPDATE alembic_version SET version_num = 'wrongrevision'`); err != nil {
			t.Fatalf("change revision: %v", err)
		}
		assertPreflightFailureLeavesIntermediateEmpty(t, conn)
	})

	t.Run("schema fingerprint", func(t *testing.T) {
		conn := connectTestPostgres(t)
		if _, err := conn.Exec(t.Context(), `ALTER TABLE visibility ADD COLUMN unexpected text`); err != nil {
			t.Fatalf("change source schema: %v", err)
		}
		assertPreflightFailureLeavesIntermediateEmpty(t, conn)
	})
}

func assertPreflightFailureLeavesIntermediateEmpty(t *testing.T, conn *pgx.Conn) {
	t.Helper()
	sqliteDB := newIntermediate(t)
	report, err := CopyPostgresToSQLite(t.Context(), conn, sqliteDB)
	if err == nil {
		t.Fatal("CopyPostgresToSQLite unexpectedly accepted source drift")
	}
	if len(report.Tables) != 0 {
		t.Errorf("preflight failure copied %d tables", len(report.Tables))
	}
	var count int
	mustScan(t, sqliteDB, `SELECT count(*) FROM mediatype`, &count)
	if count != 0 {
		t.Errorf("preflight failure left %d destination rows", count)
	}
}

func mustScan(t *testing.T, db *sql.DB, query string, dest ...any) {
	t.Helper()
	if err := db.QueryRowContext(context.Background(), query).Scan(dest...); err != nil {
		t.Fatalf("query %q: %v", query, err)
	}
}
