// Integration tests require QUAY_TEST_POSTGRES_DSN. `make go-test-postgres`
// provides a disposable PostgreSQL 16 server.
package postgres

import (
	"bytes"
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"testing"

	"github.com/jackc/pgx/v5"

	"github.com/quay/quay/internal/dal/dbcore"
)

const postgresDSNEnv = "QUAY_TEST_POSTGRES_DSN"

// This representative schema matches the real Alembic-derived fixture in
// ../testdata. Lookup IDs are intentionally different from the SQLite seed.
const postgresSchemaDDL = `
DROP TABLE IF EXISTS tag, manifest, repository, "user", visibility, repositorykind, mediatype, tagkind CASCADE;

CREATE TABLE visibility (
	id integer PRIMARY KEY,
	name varchar(255) NOT NULL
);

CREATE TABLE repositorykind (
	id integer PRIMARY KEY,
	name varchar(255) NOT NULL
);

CREATE TABLE mediatype (
	id integer PRIMARY KEY,
	name varchar(255) NOT NULL
);

CREATE TABLE tagkind (
	id integer PRIMARY KEY,
	name varchar(255) NOT NULL
);

CREATE TABLE "user" (
	id integer PRIMARY KEY,
	uuid varchar(36),
	username varchar(255) NOT NULL,
	password_hash varchar(255),
	email varchar(255) NOT NULL,
	verified boolean NOT NULL,
	stripe_id varchar(255),
	organization boolean NOT NULL,
	robot boolean NOT NULL,
	invoice_email boolean NOT NULL,
	invalid_login_attempts integer NOT NULL DEFAULT 0,
	last_invalid_login timestamp NOT NULL,
	removed_tag_expiration_s bigint NOT NULL DEFAULT 1209600,
	enabled boolean NOT NULL DEFAULT true,
	invoice_email_address varchar(255),
	company varchar(255),
	family_name varchar(255),
	given_name varchar(255),
	location varchar(255),
	maximum_queued_builds_count integer,
	creation_date timestamp,
	last_accessed timestamp
);

CREATE TABLE repository (
	id integer PRIMARY KEY,
	namespace_user_id integer,
	name varchar(255) NOT NULL,
	visibility_id integer NOT NULL,
	description text,
	badge_token varchar(255) NOT NULL,
	kind_id integer NOT NULL DEFAULT 1,
	trust_enabled boolean NOT NULL DEFAULT false,
	state integer NOT NULL DEFAULT 0
);

CREATE TABLE manifest (
	id integer PRIMARY KEY,
	repository_id integer NOT NULL,
	digest varchar(255) NOT NULL,
	media_type_id integer NOT NULL,
	manifest_bytes text NOT NULL,
	config_media_type varchar(255),
	layers_compressed_size bigint,
	subject varchar(255),
	subject_backfilled boolean,
	artifact_type varchar(255),
	artifact_type_backfilled boolean
);

CREATE TABLE tag (
	id integer PRIMARY KEY,
	name varchar(255) NOT NULL,
	repository_id integer NOT NULL,
	manifest_id integer,
	lifetime_start_ms bigint NOT NULL,
	lifetime_end_ms bigint,
	hidden boolean NOT NULL DEFAULT false,
	reversion boolean NOT NULL DEFAULT false,
	tag_kind_id integer NOT NULL,
	linked_tag_id integer
);
`

// Representative rows cover NULLs, booleans, timestamps, JSON, and tag lifetimes.
const postgresSeedDML = `
-- Deliberately swap lookup IDs relative to the SQLite baseline.
INSERT INTO visibility (id, name) VALUES (1, 'private'), (2, 'public');
INSERT INTO repositorykind (id, name) VALUES (1, 'image'), (2, 'application');
INSERT INTO tagkind (id, name) VALUES (1, 'tag');
INSERT INTO mediatype (id, name) VALUES
	(15, 'application/vnd.docker.distribution.manifest.v2+json'),
	(16, 'application/vnd.docker.distribution.manifest.list.v2+json');

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

	conn, err := pgx.Connect(t.Context(), dsn)
	if err != nil {
		t.Fatalf("connect to test postgres (%s): %v", postgresDSNEnv, err)
	}
	t.Cleanup(func() { _ = conn.Close(context.Background()) })

	if _, err := conn.Exec(t.Context(), postgresSchemaDDL); err != nil {
		t.Fatalf("create representative postgres schema: %v", err)
	}
	if _, err := conn.Exec(t.Context(), postgresSeedDML); err != nil {
		t.Fatalf("seed representative postgres data: %v", err)
	}
	return conn
}

// TestCopyPostgresToSQLite_Integration exercises the copy and bridge end to end.
func TestCopyPostgresToSQLite_Integration(t *testing.T) {
	conn := connectTestPostgres(t)

	sqlitePath := filepath.Join(t.TempDir(), "quay.db.partial")
	sqliteDB, err := dbcore.OpenSQLite(sqlitePath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	t.Cleanup(func() { _ = sqliteDB.Close() })

	var initOut, copyOut, bridgeOut bytes.Buffer
	if err := dbcore.InitOMRSourceIntermediate(t.Context(), sqliteDB, &initOut); err != nil {
		t.Fatalf("InitOMRSourceIntermediate: %v", err)
	}

	report, err := CopyPostgresToSQLite(t.Context(), conn, sqliteDB, &copyOut)
	if err != nil {
		t.Fatalf("CopyPostgresToSQLite: %v", err)
	}

	wantCounts := map[string]int64{
		"visibility": 2, "repositorykind": 2, "mediatype": 2, "tagkind": 1,
		"user": 2, "repository": 2, "manifest": 2, "tag": 3,
	}
	for table, want := range wantCounts {
		got, ok := report.Tables[table]
		if !ok {
			t.Fatalf("report missing table %s", table)
		}
		if got.SourceRows != want || got.DestRows != want {
			t.Errorf("table %s: source=%d dest=%d, want %d", table, got.SourceRows, got.DestRows, want)
		}
	}

	// The source's shuffled lookup IDs must replace the static SQLite seed.
	var visibility1Name string
	mustScan(t, sqliteDB, `SELECT name FROM visibility WHERE id = 1`, &visibility1Name)
	if visibility1Name != "private" {
		t.Errorf("visibility 1 name = %q, want the source's %q (not the baseline's \"public\")", visibility1Name, "private")
	}
	var mediatype16Name string
	mustScan(t, sqliteDB, `SELECT name FROM mediatype WHERE id = 16`, &mediatype16Name)
	const wantMediatype16 = "application/vnd.docker.distribution.manifest.list.v2+json"
	if mediatype16Name != wantMediatype16 {
		t.Errorf("mediatype 16 name = %q, want the source's %q (not the baseline's \"...manifest.v2+json\")", mediatype16Name, wantMediatype16)
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

	var repo1Desc sql.NullString
	mustScan(t, sqliteDB, `SELECT description FROM repository WHERE id = 1`, &repo1Desc)
	if repo1Desc.Valid {
		t.Errorf("repository 1 expected NULL description, got %q", repo1Desc.String)
	}

	var repo2Desc string
	var trustEnabled int64
	mustScan(t, sqliteDB, `SELECT description, trust_enabled FROM repository WHERE id = 2`, &repo2Desc, &trustEnabled)
	const wantDesc = "has a description with 'quotes' and text"
	if repo2Desc != wantDesc || trustEnabled != 1 {
		t.Errorf("repository 2 = description=%q trust_enabled=%d, want %q,1", repo2Desc, trustEnabled, wantDesc)
	}

	var subject sql.NullString
	var artifactTypeBackfilled int64
	mustScan(t, sqliteDB, `SELECT subject, artifact_type_backfilled FROM manifest WHERE id = 1`, &subject, &artifactTypeBackfilled)
	if subject.Valid || artifactTypeBackfilled != 1 {
		t.Errorf("manifest 1 = subject=%+v artifact_type_backfilled=%d, want NULL,1", subject, artifactTypeBackfilled)
	}

	var manifestBytes string
	mustScan(t, sqliteDB, `SELECT manifest_bytes FROM manifest WHERE id = 2`, &manifestBytes)
	const wantManifestBytes = `{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json","layers":[]}`
	if manifestBytes != wantManifestBytes {
		t.Errorf("manifest 2 manifest_bytes = %q, want byte-identical %q", manifestBytes, wantManifestBytes)
	}

	var hidden, reversion int64
	var linkedTagID sql.NullInt64
	var lifetimeEnd sql.NullInt64
	mustScan(t, sqliteDB, `SELECT hidden, reversion, linked_tag_id, lifetime_end_ms FROM tag WHERE id = 3`, &hidden, &reversion, &linkedTagID, &lifetimeEnd)
	if hidden != 1 || reversion != 1 || !linkedTagID.Valid || linkedTagID.Int64 != 1 || lifetimeEnd.Valid {
		t.Errorf("tag 3 = hidden=%d reversion=%d linked_tag_id=%+v lifetime_end_ms=%+v, want 1,1,{1 true},{0 false}", hidden, reversion, linkedTagID, lifetimeEnd)
	}

	var expiredLifetimeEnd sql.NullInt64
	mustScan(t, sqliteDB, `SELECT lifetime_end_ms FROM tag WHERE id = 2`, &expiredLifetimeEnd)
	if !expiredLifetimeEnd.Valid || expiredLifetimeEnd.Int64 != 1785501500000 {
		t.Errorf("tag 2 lifetime_end_ms = %+v, want 1785501500000", expiredLifetimeEnd)
	}

	// Reuse the existing SQLite admission and bridge contracts unchanged.
	if err := dbcore.ValidateSourceCompatibility(t.Context(), sqliteDB); err != nil {
		t.Fatalf("ValidateSourceCompatibility on copied intermediate: %v", err)
	}

	if err := dbcore.RunBridge(t.Context(), sqliteDB, &bridgeOut); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}

	ver, err := dbcore.SchemaVersion(t.Context(), sqliteDB)
	if err != nil {
		t.Fatalf("SchemaVersion after bridge: %v", err)
	}
	if ver != dbcore.TargetVersion {
		t.Fatalf("post-bridge version = %q, want %q", ver, dbcore.TargetVersion)
	}

	if err := dbcore.IntegrityCheck(t.Context(), sqliteDB); err != nil {
		t.Errorf("post-bridge IntegrityCheck: %v", err)
	}

	for table, want := range wantCounts {
		var got int64
		if err := sqliteDB.QueryRowContext(t.Context(), `SELECT COUNT(*) FROM "`+table+`"`).Scan(&got); err != nil {
			t.Fatalf("count %s after bridge: %v", table, err)
		}
		if got != want {
			t.Errorf("table %s row count changed during bridge: before=%d after=%d", table, want, got)
		}
	}

	// SQLite must allocate a new ID without copied PostgreSQL sequences.
	res, err := sqliteDB.ExecContext(t.Context(),
		`INSERT INTO repository (namespace_user_id, name, visibility_id, badge_token) VALUES (?, ?, ?, ?)`,
		1, "post-migration-repo", 2, "post-migration-badge-token",
	)
	if err != nil {
		t.Fatalf("post-migration insert: %v", err)
	}
	newID, err := res.LastInsertId()
	if err != nil {
		t.Fatalf("LastInsertId: %v", err)
	}
	if newID <= 2 {
		t.Errorf("post-migration repository id = %d, want > 2 (the highest copied id)", newID)
	}
}

// TestCopyPostgresToSQLite_Integration_RejectsDuplicateKey verifies rollback.
func TestCopyPostgresToSQLite_Integration_RejectsDuplicateKey(t *testing.T) {
	conn := connectTestPostgres(t)

	if _, err := conn.Exec(t.Context(), `INSERT INTO "user" (id, username, email, verified, organization, robot, invoice_email, last_invalid_login) VALUES (3, 'dup', 'dup@quay.io', false, false, false, false, now())`); err != nil {
		t.Fatalf("seed duplicate-triggering row: %v", err)
	}

	sqlitePath := filepath.Join(t.TempDir(), "quay.db.partial")
	sqliteDB, err := dbcore.OpenSQLite(sqlitePath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	t.Cleanup(func() { _ = sqliteDB.Close() })

	var initOut bytes.Buffer
	if err := dbcore.InitOMRSourceIntermediate(t.Context(), sqliteDB, &initOut); err != nil {
		t.Fatalf("InitOMRSourceIntermediate: %v", err)
	}

	// Trigger a real destination primary-key violation.
	if _, err := sqliteDB.ExecContext(t.Context(), `INSERT INTO "user" (id, username, email, verified, organization, robot, invoice_email, last_invalid_login, removed_tag_expiration_s) VALUES (1, 'preexisting', 'preexisting@quay.io', 0, 0, 0, 0, '2026-01-01 00:00:00', 1209600)`); err != nil {
		t.Fatalf("seed colliding destination row: %v", err)
	}

	var copyOut bytes.Buffer
	_, err = CopyPostgresToSQLite(t.Context(), conn, sqliteDB, &copyOut)
	if err == nil {
		t.Fatal("CopyPostgresToSQLite unexpectedly succeeded against a colliding destination row")
	}

	var count int
	if err := sqliteDB.QueryRowContext(t.Context(), `SELECT COUNT(*) FROM "user"`).Scan(&count); err != nil {
		t.Fatalf("count user after aborted copy: %v", err)
	}
	if count != 1 {
		t.Errorf("expected the aborted copy to leave only the pre-existing row (rolled back), found %d rows", count)
	}
}

func mustScan(t *testing.T, db *sql.DB, query string, dest ...any) {
	t.Helper()
	if err := db.QueryRowContext(context.Background(), query).Scan(dest...); err != nil {
		t.Fatalf("query %q: %v", query, err)
	}
}
