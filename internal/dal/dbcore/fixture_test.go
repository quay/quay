package dbcore

import (
	"bytes"
	"database/sql"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// fixturePath is the artifact-derived OMR v2.0.11 SQLite fixture. Its
// provenance (release, image, digests, extraction procedure) is recorded in
// the fixture file's own header comment and the commit that added it.
// Unlike the deleted synthetic bridge_test.go fixture that predated #6681,
// this database was produced by installing the real mirror-registry-offline
// v2.0.11 release asset, not by back-stamping a newer schema's
// alembic_version.
const fixturePath = "testdata/omr_v2.0.11_3f8d7acdf7f9.sql"

// loadFixtureDB replays the fixture dump into a fresh SQLite database and
// returns it. It fails the test outright if the fixture is missing, so an
// accidentally deleted fixture cannot silently disable convergence coverage.
func loadFixtureDB(t *testing.T) *sql.DB {
	t.Helper()

	dump, err := os.ReadFile(fixturePath)
	if err != nil {
		t.Fatalf("read fixture %s: %v", fixturePath, err)
	}

	db, err := OpenSQLite(filepath.Join(t.TempDir(), "fixture.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	// The dump may itself toggle foreign_keys and wrap in a transaction; run
	// with checks off while replaying so statement order in the historical
	// artifact doesn't matter, matching InitDatabase's own convention.
	if _, err := db.ExecContext(t.Context(), "PRAGMA foreign_keys = OFF"); err != nil {
		t.Fatalf("disable foreign keys: %v", err)
	}
	for i, stmt := range splitStatements(string(dump)) {
		trimmed := strings.TrimSpace(stmt)
		if trimmed == "" || strings.HasPrefix(strings.ToUpper(trimmed), "BEGIN") || strings.HasPrefix(strings.ToUpper(trimmed), "COMMIT") {
			continue
		}
		if _, err := db.ExecContext(t.Context(), stmt); err != nil {
			t.Fatalf("replay fixture statement %d: %v\nstatement: %s", i, err, truncate(trimmed, 200))
		}
	}
	if _, err := db.ExecContext(t.Context(), "PRAGMA foreign_keys = ON"); err != nil {
		t.Fatalf("re-enable foreign keys: %v", err)
	}

	return db
}

func TestRunBridge_ConvergesArtifactFixture(t *testing.T) {
	db := loadFixtureDB(t)

	ver, err := SchemaVersion(t.Context(), db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if ver != ApprovedOMRSourceVersion {
		t.Fatalf("fixture alembic_version = %q, want %q", ver, ApprovedOMRSourceVersion)
	}
	if err := IntegrityCheck(t.Context(), db); err != nil {
		t.Fatalf("pre-bridge IntegrityCheck: %v", err)
	}

	dataTables := []string{"repository", "tag", manifestTable}
	before := tableCounts(t, db, dataTables)

	var logs bytes.Buffer
	previousLogger := slog.Default()
	slog.SetDefault(slog.New(slog.NewJSONHandler(&logs, nil)))
	t.Cleanup(func() { slog.SetDefault(previousLogger) })

	if err := RunBridge(t.Context(), db); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}
	if got := logs.String(); !strings.Contains(got, `"msg":"bridging schema"`) || !strings.Contains(got, `"msg":"schema bridged"`) {
		t.Errorf("structured bridge logs missing: %s", got)
	}

	ver, err = SchemaVersion(t.Context(), db)
	if err != nil {
		t.Fatalf("SchemaVersion after bridge: %v", err)
	}
	if ver != TargetVersion {
		t.Fatalf("post-bridge version = %q, want %q", ver, TargetVersion)
	}

	if err := IntegrityCheck(t.Context(), db); err != nil {
		t.Errorf("post-bridge IntegrityCheck: %v", err)
	}
	if err := ForeignKeyCheck(t.Context(), db); err != nil {
		t.Errorf("post-bridge foreign key check: %v", err)
	}

	after := tableCounts(t, db, dataTables)
	for _, table := range dataTables {
		if before[table] == 0 {
			t.Errorf("fixture has no %s rows; it does not exercise the data-preservation assertions below", table)
		}
		if got, want := after[table], before[table]; got != want {
			t.Errorf("%s row count changed during bridge: before=%d after=%d", table, want, got)
		}
	}

	for _, col := range bridgeColumns {
		assertColumnExists(t, db, col.table, col.column)
	}
	for _, idx := range bridgeIndexFixes {
		assertIndexExists(t, db, idx.indexName)
	}
	for name, want := range map[string]string{
		"oauthaccesstoken_application_id_last_accessed": "CREATE INDEX oauthaccesstoken_application_id_last_accessed ON oauthaccesstoken (application_id, last_accessed)",
		"user_email_unique_non_org":                     `CREATE UNIQUE INDEX user_email_unique_non_org ON "user" (email) WHERE organization = false`,
		"user_email_idx":                                `CREATE INDEX user_email_idx ON "user" (email)`,
	} {
		assertIndexDefinition(t, db, name, want)
	}
	assertIndexMissing(t, db, "user_email")
	for _, table := range []string{
		"tagpullstatistics", "manifestpullstatistics", "orgmirrorconfig",
		"orgmirrorrepository", "namespaceimmutabilitypolicy",
		"repositoryimmutabilitypolicy", "organizationcontactemail",
		"namespacenotification", "quotanotificationstate",
	} {
		assertTableExists(t, db, table)
	}
}

func TestRunBridge_RejectsMarkerTamperedArtifactFixture(t *testing.T) {
	db := loadFixtureDB(t)

	if _, err := db.ExecContext(t.Context(), "UPDATE alembic_version SET version_num = ?", "ffffffffffff"); err != nil {
		t.Fatalf("tamper marker: %v", err)
	}

	err := RunBridge(t.Context(), db)
	if err == nil || !strings.Contains(err.Error(), "unsupported OMR source revision") {
		t.Fatalf("RunBridge error = %v, want source rejection", err)
	}
}

// TestRunBridge_RejectsStructurallyAlteredArtifactFixture proves that a "3f8"
// database that does not actually match the real artifact's structure still
// fails closed today, via RunBridge/applyBridge's existing schema-mutation
// error paths. This intentionally does not add a new structural-profile
// check to production code; wiring the fixture's schema fingerprint into
// runtime admission (ValidateSourceCompatibility) is deferred follow-up work,
// tracked separately from this fixture/test-only change.
func TestRunBridge_RejectsStructurallyAlteredArtifactFixture(t *testing.T) {
	db := loadFixtureDB(t)

	// Drop a table that bridgeColumns' ensureColumn targets directly
	// (bridge.go adds tag.immutable), simulating a hand-edited "3f8" source
	// missing an expected table rather than one produced by the real OMR
	// artifact. applyBridge's own ALTER TABLE call fails closed on the
	// resulting "no such table" error; this is RunBridge's existing
	// behavior, not a new check added for this test.
	if _, err := db.ExecContext(t.Context(), `DROP TABLE "tag"`); err != nil {
		t.Fatalf("mutate fixture: %v", err)
	}

	err := RunBridge(t.Context(), db)
	if err == nil {
		t.Fatal("RunBridge unexpectedly succeeded against a structurally altered fixture")
	}
	if !strings.Contains(err.Error(), "no such table: tag") {
		t.Errorf("RunBridge error = %v, want it to report the missing tag table", err)
	}

	// RunBridge disables foreign_keys before its transaction and re-enables
	// them via a deferred call regardless of outcome; a failed bridge must
	// not leave enforcement off.
	var foreignKeysEnabled int
	if err := db.QueryRowContext(t.Context(), "PRAGMA foreign_keys").Scan(&foreignKeysEnabled); err != nil {
		t.Fatalf("query foreign_keys pragma: %v", err)
	}
	if foreignKeysEnabled != 1 {
		t.Error("expected foreign_keys to be re-enabled after a failed RunBridge")
	}
}

func tableCounts(t *testing.T, db *sql.DB, tables []string) map[string]int {
	t.Helper()
	counts := make(map[string]int, len(tables))
	for _, table := range tables {
		var n int
		if err := db.QueryRowContext(t.Context(), fmt.Sprintf("SELECT COUNT(*) FROM %q", table)).Scan(&n); err != nil {
			t.Fatalf("count %s: %v", table, err)
		}
		counts[table] = n
	}
	return counts
}

func assertColumnExists(t *testing.T, db *sql.DB, table, column string) {
	t.Helper()
	var n int
	q := "SELECT count(*) FROM pragma_table_info(?) WHERE name=?"
	if err := db.QueryRowContext(t.Context(), q, table, column).Scan(&n); err != nil {
		t.Fatalf("check column %s.%s: %v", table, column, err)
	}
	if n != 1 {
		t.Errorf("expected column %s.%s to exist after bridge", table, column)
	}
}

func assertIndexExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var n int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM sqlite_master WHERE type='index' AND name=?", name).Scan(&n); err != nil {
		t.Fatalf("check index %s: %v", name, err)
	}
	if n != 1 {
		t.Errorf("expected index %s to exist after bridge", name)
	}
}

func assertIndexDefinition(t *testing.T, db *sql.DB, name, want string) {
	t.Helper()
	var got string
	if err := db.QueryRowContext(t.Context(), "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", name).Scan(&got); err != nil {
		t.Fatalf("read index %s: %v", name, err)
	}
	normalize := func(s string) string { return strings.Join(strings.Fields(s), " ") }
	if normalize(got) != normalize(want) {
		t.Errorf("index %s = %q, want %q", name, got, want)
	}
}

func assertIndexMissing(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var n int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM sqlite_master WHERE type='index' AND name=?", name).Scan(&n); err != nil {
		t.Fatalf("check index %s: %v", name, err)
	}
	if n != 0 {
		t.Errorf("expected index %s to be absent after bridge", name)
	}
}

func assertTableExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var n int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", name).Scan(&n); err != nil {
		t.Fatalf("check table %s: %v", name, err)
	}
	if n != 1 {
		t.Errorf("expected table %s to exist after bridge", name)
	}
}
