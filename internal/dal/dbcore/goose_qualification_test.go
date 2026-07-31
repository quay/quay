package dbcore

import (
	"context"
	"database/sql"
	"embed"
	"errors"
	"io"
	"io/fs"
	"path/filepath"
	"slices"
	"sync"
	"testing"
	"testing/fstest"

	"github.com/pressly/goose/v3"
)

// This file is a test-only qualification prototype for adopting
// github.com/pressly/goose/v3 as a future native SQLite migration engine.
// It proves the dependency's provider API, driver compatibility, and
// transaction semantics work against this package's existing
// modernc.org/sqlite setup (see OpenSQLite in sqlite.go). It does not wire
// goose into any production path: Setup, ensureSchema, RunBridge, and
// InitDatabase are all untouched, and no goose ledger table is ever created
// outside of this file's own tests.
//
// gooseQualificationFixtures embeds a small, deliberately synthetic
// migration set (unrelated to the real Quay/OMR schema) used only to
// exercise goose's SQL statement parser, including a trigger body with
// internal semicolons.
//
//go:embed testdata/goose/*.sql
var gooseQualificationFixtures embed.FS

func gooseQualificationFS(t *testing.T) fs.FS {
	t.Helper()
	sub, err := fs.Sub(gooseQualificationFixtures, "testdata/goose")
	if err != nil {
		t.Fatalf("fs.Sub: %v", err)
	}
	return sub
}

// TestGooseQualification_SingleSQLiteDriver proves that importing goose does
// not register a second (or competing) database/sql driver. goose's provider
// API takes a caller-supplied *sql.DB and never imports a driver package
// itself; this asserts that invariant holds for the version pinned here.
func TestGooseQualification_SingleSQLiteDriver(t *testing.T) {
	got := sql.Drivers() // already sorted, per database/sql docs.
	want := []string{"sqlite"}
	if !slices.Equal(got, want) {
		t.Fatalf("registered database/sql drivers = %v, want %v", got, want)
	}
}

// TestGooseQualification_ProviderHasNoGlobalState proves that goose.Provider
// options (such as a custom version-table name) are scoped to the provider
// instance they were built with, not to any package-level variable. This
// codebase only ever uses goose.NewProvider, never the deprecated
// package-level goose.SetDialect/goose.Up functions, specifically to avoid
// shared mutable state between independent migration runs.
func TestGooseQualification_ProviderHasNoGlobalState(t *testing.T) {
	ctx := t.Context()
	fsys := gooseQualificationFS(t)

	dbA, err := OpenSQLite(filepath.Join(t.TempDir(), "a.db"))
	if err != nil {
		t.Fatalf("OpenSQLite A: %v", err)
	}
	defer dbA.Close()

	dbB, err := OpenSQLite(filepath.Join(t.TempDir(), "b.db"))
	if err != nil {
		t.Fatalf("OpenSQLite B: %v", err)
	}
	defer dbB.Close()

	providerA, err := goose.NewProvider(goose.DialectSQLite3, dbA, fsys, goose.WithTableName("custom_ledger"))
	if err != nil {
		t.Fatalf("NewProvider A: %v", err)
	}
	if _, err := providerA.Up(ctx); err != nil {
		t.Fatalf("Up A: %v", err)
	}

	// providerB is constructed after providerA with no table-name option.
	// If goose tracked the table name as package-global state, B would
	// inherit A's "custom_ledger" name instead of goose.DefaultTablename.
	providerB, err := goose.NewProvider(goose.DialectSQLite3, dbB, fsys)
	if err != nil {
		t.Fatalf("NewProvider B: %v", err)
	}
	if _, err := providerB.Up(ctx); err != nil {
		t.Fatalf("Up B: %v", err)
	}

	assertTableExists(t, dbA, "custom_ledger")
	assertTableNotExists(t, dbA, goose.DefaultTablename)
	assertTableExists(t, dbB, goose.DefaultTablename)
	assertTableNotExists(t, dbB, "custom_ledger")
}

// TestGooseQualification_EmbeddedTriggerMigrations runs the embedded
// fixture migrations (including a trigger whose body contains internal
// semicolons) against a real OpenSQLite-managed database that already has
// the production Quay/OMR schema (and its alembic_version table) loaded,
// proving:
//   - embedded SQL with triggers and internal semicolons parses correctly;
//   - goose's own version table coexists with alembic_version without
//     collision or interference;
//   - migrations run through goose's transactions inherit this codebase's
//     connection PRAGMAs unchanged.
func TestGooseQualification_EmbeddedTriggerMigrations(t *testing.T) {
	ctx := t.Context()
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "quay.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	if err := InitDatabase(ctx, db, io.Discard); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	beforePragmas := readPragmas(t, db)

	provider, err := goose.NewProvider(goose.DialectSQLite3, db, gooseQualificationFS(t))
	if err != nil {
		t.Fatalf("NewProvider: %v", err)
	}

	results, err := provider.Up(ctx)
	if err != nil {
		t.Fatalf("Up: %v", err)
	}
	if len(results) != 2 {
		t.Fatalf("applied %d migrations, want 2", len(results))
	}

	version, err := provider.GetDBVersion(ctx)
	if err != nil {
		t.Fatalf("GetDBVersion: %v", err)
	}
	if version != 2 {
		t.Fatalf("goose version = %d, want 2", version)
	}

	// The OMR compatibility layer's own version tracking must be untouched
	// by an unrelated goose migration run against the same database.
	alembicVersion, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if alembicVersion != TargetVersion {
		t.Fatalf("alembic_version = %q after unrelated goose migrations, want unchanged %q", alembicVersion, TargetVersion)
	}
	assertTableExists(t, db, goose.DefaultTablename)

	// Exercise the trigger: both statements inside its
	// StatementBegin/StatementEnd body must have run.
	if _, err := db.ExecContext(ctx, "INSERT INTO widget (name, status) VALUES (?, ?)", "left-pad", "active"); err != nil {
		t.Fatalf("insert widget: %v", err)
	}
	var auditCount int
	if err := db.QueryRowContext(ctx, "SELECT count(*) FROM widget_audit WHERE action = 'insert'").Scan(&auditCount); err != nil {
		t.Fatalf("count widget_audit: %v", err)
	}
	if auditCount != 1 {
		t.Fatalf("widget_audit rows = %d, want 1 (trigger with internal semicolons did not fire)", auditCount)
	}
	var updatedAt sql.NullString
	if err := db.QueryRowContext(ctx, "SELECT updated_at FROM widget WHERE name = 'left-pad'").Scan(&updatedAt); err != nil {
		t.Fatalf("select widget.updated_at: %v", err)
	}
	if !updatedAt.Valid || updatedAt.String == "" {
		t.Fatal("trigger's second (UPDATE) statement did not run")
	}

	// goose runs each migration in a transaction on a *sql.Conn drawn from
	// the same *sql.DB that OpenSQLite configured (MaxOpenConns=1, so it is
	// physically the same connection throughout). Confirm PRAGMAs survived.
	afterPragmas := readPragmas(t, db)
	if afterPragmas != beforePragmas {
		t.Fatalf("connection PRAGMAs changed across goose migrations: before=%+v after=%+v", beforePragmas, afterPragmas)
	}
}

// TestGooseQualification_DownMigrationsRestoreSchema proves the embedded
// fixture's Down scripts are the true inverse of their Up scripts. In
// particular, 00002_widget_status.sql's Down script must drop
// widget_status_idx before dropping the widget.status column: SQLite
// rejects an ALTER TABLE ... DROP COLUMN for a column a surviving index
// still references. goose applies Down scripts in descending version
// order, so a successful DownTo(0) below exercises that ordering for real
// instead of only by inspection.
func TestGooseQualification_DownMigrationsRestoreSchema(t *testing.T) {
	ctx := t.Context()
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "down.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	if err := InitDatabase(ctx, db, io.Discard); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}

	provider, err := goose.NewProvider(goose.DialectSQLite3, db, gooseQualificationFS(t))
	if err != nil {
		t.Fatalf("NewProvider: %v", err)
	}

	if _, err := provider.Up(ctx); err != nil {
		t.Fatalf("Up: %v", err)
	}
	assertTableExists(t, db, "widget")
	assertIndexExists(t, db, "widget_status_idx")

	if _, err := provider.DownTo(ctx, 0); err != nil {
		t.Fatalf("DownTo(0): %v", err)
	}

	version, err := provider.GetDBVersion(ctx)
	if err != nil {
		t.Fatalf("GetDBVersion: %v", err)
	}
	if version != 0 {
		t.Fatalf("goose version = %d after DownTo(0), want 0", version)
	}

	// Both migrations' additions must be fully reverted. goose's own
	// version table (goose_db_version) intentionally persists across
	// DownTo(0) -- only its rows are cleared, not the table itself -- so it
	// is not part of this "restored" assertion set.
	assertTableNotExists(t, db, "widget")
	assertTableNotExists(t, db, "widget_audit")
	assertIndexNotExists(t, db, "widget_status_idx")
	assertTriggerNotExists(t, db, "widget_audit_insert")

	// The unrelated OMR compatibility version stamp must be untouched.
	alembicVersion, err := SchemaVersion(ctx, db)
	if err != nil {
		t.Fatalf("SchemaVersion: %v", err)
	}
	if alembicVersion != TargetVersion {
		t.Fatalf("alembic_version = %q after goose DownTo(0), want unchanged %q", alembicVersion, TargetVersion)
	}
}

// TestGooseQualification_FailedMigrationRollsBackAtomically proves that a
// multi-statement migration is atomic: when a later statement fails, an
// earlier statement's effect in the same file is rolled back too, and no
// version is recorded. This is what lets OpenSQLite's DSN omit
// "_txlock=immediate" for goose the same way it already does for this
// package's own hand-written transactions (see sqlite.go): with
// MaxOpenConns(1) there is never a second connection racing to upgrade a
// deferred transaction to a write lock, so BeginTx's default (DEFERRED)
// lock mode is sufficient.
func TestGooseQualification_FailedMigrationRollsBackAtomically(t *testing.T) {
	ctx := t.Context()
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "rollback.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	// One migration file is one transaction by default (no
	// "-- +goose NO TRANSACTION" marker). The second statement fails, so
	// the first statement's CREATE TABLE must not persist.
	fsys := fstest.MapFS{
		"00001_broken.sql": &fstest.MapFile{Data: []byte(
			"-- +goose Up\n" +
				"CREATE TABLE should_not_persist (id INTEGER PRIMARY KEY);\n" +
				"INSERT INTO no_such_table (id) VALUES (1);\n",
		)},
	}

	provider, err := goose.NewProvider(goose.DialectSQLite3, db, fsys)
	if err != nil {
		t.Fatalf("NewProvider: %v", err)
	}

	if _, err := provider.Up(ctx); err == nil {
		t.Fatal("Up succeeded, want an error from the invalid second statement")
	}

	assertTableNotExists(t, db, "should_not_persist")
	version, err := provider.GetDBVersion(ctx)
	if err != nil {
		t.Fatalf("GetDBVersion: %v", err)
	}
	if version != 0 {
		t.Fatalf("goose version = %d after a failed migration, want 0", version)
	}
}

// TestGooseQualification_ContextCancellationRollsBackAndIsRetryable proves
// that an already-canceled context both prevents a migration from applying
// and leaves the database in a state a later, valid call can still use.
func TestGooseQualification_ContextCancellationRollsBackAndIsRetryable(t *testing.T) {
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "cancel.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	fsys := fstest.MapFS{
		"00001_widgets.sql": &fstest.MapFile{Data: []byte(
			"-- +goose Up\n" +
				"CREATE TABLE cancel_target (id INTEGER PRIMARY KEY);\n",
		)},
	}

	provider, err := goose.NewProvider(goose.DialectSQLite3, db, fsys)
	if err != nil {
		t.Fatalf("NewProvider: %v", err)
	}

	canceledCtx, cancel := context.WithCancel(t.Context())
	cancel()

	_, err = provider.Up(canceledCtx)
	if err == nil {
		t.Fatal("Up succeeded with an already-canceled context")
	}
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("Up error = %v, want context.Canceled", err)
	}
	assertTableNotExists(t, db, "cancel_target")

	// A canceled attempt must not leave the connection, provider, or
	// version table in a state that blocks a subsequent, valid run.
	if _, err := provider.Up(t.Context()); err != nil {
		t.Fatalf("Up after canceled attempt: %v", err)
	}
	assertTableExists(t, db, "cancel_target")
}

// TestGooseQualification_VersionTableNaming proves goose's version table
// does not collide with the existing alembic_version table, and that the
// table name is controllable via WithTableName rather than only accepted
// as an opaque default.
func TestGooseQualification_VersionTableNaming(t *testing.T) {
	ctx := t.Context()

	if goose.DefaultTablename == "alembic_version" {
		t.Fatal("goose's default version table name collides with alembic_version")
	}

	db, err := OpenSQLite(filepath.Join(t.TempDir(), "collision.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()
	if err := InitDatabase(ctx, db, io.Discard); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	assertTableExists(t, db, "alembic_version")

	noop := fstest.MapFS{
		"00001_noop.sql": &fstest.MapFile{Data: []byte("-- +goose Up\nSELECT 1;\n")},
	}

	provider, err := goose.NewProvider(goose.DialectSQLite3, db, noop)
	if err != nil {
		t.Fatalf("NewProvider: %v", err)
	}
	if _, err := provider.Up(ctx); err != nil {
		t.Fatalf("Up: %v", err)
	}
	assertTableExists(t, db, goose.DefaultTablename)

	customDB, err := OpenSQLite(filepath.Join(t.TempDir(), "custom.db"))
	if err != nil {
		t.Fatalf("OpenSQLite custom: %v", err)
	}
	defer customDB.Close()

	customProvider, err := goose.NewProvider(goose.DialectSQLite3, customDB, noop, goose.WithTableName("quay_native_schema_version"))
	if err != nil {
		t.Fatalf("NewProvider custom: %v", err)
	}
	if _, err := customProvider.Up(ctx); err != nil {
		t.Fatalf("Up custom: %v", err)
	}
	assertTableExists(t, customDB, "quay_native_schema_version")
	assertTableNotExists(t, customDB, goose.DefaultTablename)
}

// TestGooseQualification_SerializesThroughSingleConnection proves that,
// for the pinned github.com/pressly/goose/v3 v3.27.3 release, independent
// goose.Provider instances sharing one OpenSQLite *sql.DB (MaxOpenConns=1)
// apply migrations safely under concurrent use: Go's *sql.DB connection
// pool serializes access to the single physical connection rather than
// surfacing SQLite "database is locked" errors. This is the concrete
// behavioral basis, as of this pinned goose version, for not needing
// "_txlock=immediate" in this codebase's DSN. goose's internal connection
// acquisition (Provider.initialize calling db.Conn(ctx)) is an
// implementation detail of that version, not a documented contract, so
// this test must be re-run (and "_txlock=immediate" reassessed) whenever
// the pinned goose version changes.
func TestGooseQualification_SerializesThroughSingleConnection(t *testing.T) {
	ctx := t.Context()
	db, err := OpenSQLite(filepath.Join(t.TempDir(), "serialize.db"))
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	defer db.Close()

	fsys := gooseQualificationFS(t)
	const attempts = 5
	providers := make([]*goose.Provider, attempts)
	for i := range providers {
		p, err := goose.NewProvider(goose.DialectSQLite3, db, fsys)
		if err != nil {
			t.Fatalf("NewProvider[%d]: %v", i, err)
		}
		providers[i] = p
	}

	var wg sync.WaitGroup
	errs := make(chan error, attempts)
	for _, p := range providers {
		wg.Add(1)
		go func(p *goose.Provider) {
			defer wg.Done()
			_, err := p.Up(ctx)
			errs <- err
		}(p)
	}
	wg.Wait()
	close(errs)

	for err := range errs {
		if err != nil {
			t.Errorf("concurrent Up: %v", err)
		}
	}

	version, err := providers[0].GetDBVersion(ctx)
	if err != nil {
		t.Fatalf("GetDBVersion: %v", err)
	}
	if version != 2 {
		t.Fatalf("goose version = %d, want 2", version)
	}
}

type sqlitePragmas struct {
	foreignKeys int
	journalMode string
	busyTimeout int
}

func readPragmas(t *testing.T, db *sql.DB) sqlitePragmas {
	t.Helper()
	ctx := t.Context()
	var p sqlitePragmas
	if err := db.QueryRowContext(ctx, "PRAGMA foreign_keys").Scan(&p.foreignKeys); err != nil {
		t.Fatalf("PRAGMA foreign_keys: %v", err)
	}
	if err := db.QueryRowContext(ctx, "PRAGMA journal_mode").Scan(&p.journalMode); err != nil {
		t.Fatalf("PRAGMA journal_mode: %v", err)
	}
	if err := db.QueryRowContext(ctx, "PRAGMA busy_timeout").Scan(&p.busyTimeout); err != nil {
		t.Fatalf("PRAGMA busy_timeout: %v", err)
	}
	return p
}

// assertTableExists is defined in fixture_test.go and shared across this
// package's test files.

func assertTableNotExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var n int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", name).Scan(&n); err != nil {
		t.Fatalf("check table %s: %v", name, err)
	}
	if n != 0 {
		t.Fatalf("table %s exists, want absent", name)
	}
}

func assertIndexNotExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var n int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM sqlite_master WHERE type='index' AND name=?", name).Scan(&n); err != nil {
		t.Fatalf("check index %s: %v", name, err)
	}
	if n != 0 {
		t.Fatalf("index %s exists, want absent", name)
	}
}

func assertTriggerNotExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var n int
	if err := db.QueryRowContext(t.Context(), "SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name=?", name).Scan(&n); err != nil {
		t.Fatalf("check trigger %s: %v", name, err)
	}
	if n != 0 {
		t.Fatalf("trigger %s exists, want absent", name)
	}
}
