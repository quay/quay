package dbcore

import (
	"bytes"
	"database/sql"
	"os"
	"strings"
	"testing"
)

const flawedBridgeVersion = "a2fc72f380b7"

func TestRunBridge_RepairsHistoricalC3SchemaConvergence(t *testing.T) {
	db := openBridgeFixture(t, "sqlite_c3d4e5f6a7b8_minimal.sql")
	for _, index := range []string{
		"namespaceautoprunepolicy_namespace_id",
		"repositoryautoprunepolicy_repository_id",
		"organizationrhskus_subscription_id",
	} {
		assertIndexSQLContains(t, db, index, "CREATE INDEX")
	}
	for _, index := range []string{
		"organizationrhskus_subscription_id_org_id",
		"organizationrhskus_subscription_id_org_id_user_id",
	} {
		assertIndexSQLContains(t, db, index, "UNIQUE")
	}

	if err := RunBridge(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}

	assertBridgeSchemaConverged(t, db)
	assertSchemaVersion(t, db, TargetVersion)
	assertSingleVersionMarker(t, db)

	var copiedLongEmail int
	if err := db.QueryRowContext(t.Context(),
		`SELECT count(*) FROM organizationcontactemail WHERE organization_id = 3`,
	).Scan(&copiedLongEmail); err != nil {
		t.Fatal(err)
	}
	if copiedLongEmail != 0 {
		t.Fatal("bridge copied an organization email excluded by 414c5e2fc487's length guard")
	}

	var placeholderContact string
	if err := db.QueryRowContext(t.Context(),
		`SELECT contact_email FROM organizationcontactemail WHERE organization_id = 4`,
	).Scan(&placeholderContact); err != nil {
		t.Fatal(err)
	}
	if placeholderContact != "copied-placeholder-without-at-sign" {
		t.Fatalf("placeholder contact = %q, want preserved", placeholderContact)
	}
}

func TestRunBridge_RepairsPreviouslyFlawedA2FCSchema(t *testing.T) {
	db := openBridgeFixture(t, "sqlite_a2fc72f380b7_flawed_bridge.sql")

	assertSchemaVersion(t, db, flawedBridgeVersion)
	assertSingleVersionMarker(t, db)
	assertFlawedA2FCBridgeArtifacts(t, db)
	assertTagIndexes(t, db)

	var output bytes.Buffer
	if err := RunBridge(t.Context(), db, &output); err != nil {
		t.Fatalf("RunBridge: %v", err)
	}

	for _, skippedMigration := range []string{"0001_bridge_from_omr.sql", "0002_tag_active_unique_index.sql"} {
		if strings.Contains(output.String(), skippedMigration) {
			t.Errorf("a2fc repair unexpectedly reran %s:\n%s", skippedMigration, output.String())
		}
	}
	if strings.Contains(output.String(), "Bridging schema") {
		t.Fatalf("a2fc repair unexpectedly entered the OMR bridge path:\n%s", output.String())
	}
	if !strings.Contains(output.String(), "Applying: 0003_repair_bridge_schema_convergence.sql") ||
		!strings.Contains(output.String(), "Migration complete: 1 migration(s) applied") {
		t.Fatalf("a2fc repair did not apply only 0003:\n%s", output.String())
	}

	assertBridgeSchemaConverged(t, db)
	assertTagIndexes(t, db)
	assertSchemaVersion(t, db, TargetVersion)
	assertSingleVersionMarker(t, db)

	var preservedLongContact int
	if err := db.QueryRowContext(t.Context(),
		`SELECT count(*) FROM organizationcontactemail WHERE organization_id = 3`,
	).Scan(&preservedLongContact); err != nil {
		t.Fatal(err)
	}
	if preservedLongContact != 1 {
		t.Fatalf("previously copied long organization contact count = %d, want preserved", preservedLongContact)
	}
}

func TestKnownOMRVersions_ContainsSkippedAlembicRevisions(t *testing.T) {
	for _, revision := range []string{"c3d4e5f6a7b8", "b1a79fa8e630", "d064a4f00d4a"} {
		if !knownOMRVersions[revision] {
			t.Errorf("knownOMRVersions is missing %s", revision)
		}
	}
}

func openBridgeFixture(t *testing.T, filename string) *sql.DB {
	t.Helper()
	db := openTestDB(t)
	t.Cleanup(func() { _ = db.Close() })

	fixtureSQL, err := os.ReadFile("testdata/" + filename)
	if err != nil {
		t.Fatalf("read historical fixture: %v", err)
	}
	if _, err := db.ExecContext(t.Context(), string(fixtureSQL)); err != nil {
		t.Fatalf("load historical fixture: %v", err)
	}
	return db
}

func assertFlawedA2FCBridgeArtifacts(t *testing.T, db *sql.DB) {
	t.Helper()
	ctx := t.Context()

	for _, table := range []string{
		"tagpullstatistics",
		"manifestpullstatistics",
		"orgmirrorconfig",
		"orgmirrorrepository",
		"namespaceimmutabilitypolicy",
		"repositoryimmutabilitypolicy",
		"namespacenotification",
		"quotanotificationstate",
	} {
		var count int
		if err := db.QueryRowContext(ctx,
			`SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = ?`, table,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 1 {
			t.Errorf("pre-fix 0001 table %s count = %d, want 1", table, count)
		}
	}

	for _, column := range []struct{ table, name string }{
		{table: "tag", name: "immutable"},
		{table: manifestTable, name: "artifact_type"},
		{table: manifestTable, name: "artifact_type_backfilled"},
		{table: repoMirrorConfigTable, name: "skopeo_timeout"},
		{table: repoMirrorConfigTable, name: "architecture_filter"},
	} {
		assertColumnCount(t, db, column.table, column.name, 1)
	}

	for _, kind := range []string{
		"change_tag_immutability",
		"org_mirror_enabled",
		"create_immutability_policy",
		"create_namespace_notification",
	} {
		var count int
		if err := db.QueryRowContext(ctx,
			`SELECT count(*) FROM logentrykind WHERE name = ?`, kind,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 1 {
			t.Errorf("pre-fix 0001 log seed %s count = %d, want 1", kind, count)
		}
	}
	for _, event := range []string{"quota_warning", "quota_error"} {
		var count int
		if err := db.QueryRowContext(ctx,
			`SELECT count(*) FROM externalnotificationevent WHERE name = ?`, event,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 1 {
			t.Errorf("pre-fix 0001 event seed %s count = %d, want 1", event, count)
		}
	}

	assertIndexSQLContains(t, db, "user_email", "UNIQUE")
	assertIndexAbsent(t, db, "user_email_unique_non_org")
	assertIndexAbsent(t, db, "user_email_idx")
	assertIndexAbsent(t, db, "oauthaccesstoken_application_id_last_accessed")
	for _, column := range []string{oauthCreatedColumn, oauthLastAccessedColumn, oauthDisplayNameColumn} {
		assertColumnCount(t, db, "oauthaccesstoken", column, 0)
	}
	for _, kind := range []string{createOAuthAPILogKind, revokeOAuthAPILogKind} {
		var count int
		if err := db.QueryRowContext(ctx,
			`SELECT count(*) FROM logentrykind WHERE name = ?`, kind,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 0 {
			t.Errorf("pre-fix omitted log seed %s count = %d, want 0", kind, count)
		}
	}
}

func assertColumnCount(t *testing.T, db *sql.DB, table, column string, want int) {
	t.Helper()
	var got int
	if err := db.QueryRowContext(t.Context(),
		`SELECT count(*) FROM pragma_table_info(?) WHERE name = ?`, table, column,
	).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Errorf("%s.%s column count = %d, want %d", table, column, got, want)
	}
}

func assertBridgeSchemaConverged(t *testing.T, db *sql.DB) {
	t.Helper()
	ctx := t.Context()

	var restored, existing string
	if err := db.QueryRowContext(ctx, `SELECT email FROM user WHERE id = 1`).Scan(&restored); err != nil {
		t.Fatal(err)
	}
	if restored != "restored@example.com" {
		t.Errorf("restored organization email = %q", restored)
	}
	if err := db.QueryRowContext(ctx, `SELECT email FROM user WHERE id = 5`).Scan(&existing); err != nil {
		t.Fatal(err)
	}
	if existing != "existing@example.com" {
		t.Errorf("existing organization email was overwritten with %q", existing)
	}

	assertIndexSQLContains(t, db, "user_email_unique_non_org", "UNIQUE", "WHERE ORGANIZATION = FALSE")
	assertIndexSQLContains(t, db, "user_email_idx", "CREATE INDEX")
	assertIndexAbsent(t, db, "user_email")
	assertIndexColumns(t, db, "oauthaccesstoken_application_id_last_accessed", "application_id,last_accessed")

	for _, column := range []struct {
		name, wantType string
	}{
		{name: oauthCreatedColumn, wantType: sqliteDateTimeType},
		{name: oauthLastAccessedColumn, wantType: sqliteDateTimeType},
		{name: oauthDisplayNameColumn, wantType: sqliteVarchar255Type},
	} {
		var gotType string
		var notNull int
		if err := db.QueryRowContext(ctx,
			`SELECT type, "notnull" FROM pragma_table_info('oauthaccesstoken') WHERE name = ?`,
			column.name,
		).Scan(&gotType, &notNull); err != nil {
			t.Fatalf("oauthaccesstoken.%s: %v", column.name, err)
		}
		if !strings.EqualFold(gotType, column.wantType) || notNull != 0 {
			t.Errorf("oauthaccesstoken.%s = type %q notnull %d", column.name, gotType, notNull)
		}
	}

	for _, kind := range []string{createOAuthAPILogKind, revokeOAuthAPILogKind} {
		var count int
		if err := db.QueryRowContext(ctx,
			`SELECT count(*) FROM logentrykind WHERE name = ?`, kind,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 1 {
			t.Errorf("logentrykind %q count = %d, want 1", kind, count)
		}
	}

	if _, err := db.ExecContext(ctx,
		`INSERT INTO user (
			id, username, email, verified, organization, robot, invoice_email,
			invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled
		) VALUES (6, 'shared-email-org', 'member@example.com', 1, 1, 0, 0, 0,
			'2026-01-01 00:00:00', 1209600, 1)`,
	); err != nil {
		t.Fatalf("organization should be allowed to share email: %v", err)
	}
	if _, err := db.ExecContext(ctx,
		`INSERT INTO user (
			id, username, email, verified, organization, robot, invoice_email,
			invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled
		) VALUES (7, 'duplicate-member', 'member@example.com', 1, 0, 0, 0, 0,
			'2026-01-01 00:00:00', 1209600, 1)`,
	); err == nil {
		t.Fatal("partial unique email index accepted duplicate non-organization email")
	}
}

func assertIndexSQLContains(t *testing.T, db *sql.DB, name string, fragments ...string) {
	t.Helper()
	var indexSQL string
	if err := db.QueryRowContext(t.Context(),
		`SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?`, name,
	).Scan(&indexSQL); err != nil {
		t.Fatalf("query index %s: %v", name, err)
	}
	upperSQL := strings.ToUpper(indexSQL)
	for _, fragment := range fragments {
		if !strings.Contains(upperSQL, fragment) {
			t.Errorf("index %s SQL %q does not contain %q", name, indexSQL, fragment)
		}
	}
}

func assertIndexAbsent(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var count int
	if err := db.QueryRowContext(t.Context(),
		`SELECT count(*) FROM sqlite_master WHERE type = 'index' AND name = ?`, name,
	).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Errorf("index %s still exists", name)
	}
}

func assertIndexColumns(t *testing.T, db *sql.DB, name, want string) {
	t.Helper()
	var got string
	if err := db.QueryRowContext(t.Context(),
		`SELECT group_concat(name, ',') FROM (
			SELECT name FROM pragma_index_info(?) ORDER BY seqno
		)`, name,
	).Scan(&got); err != nil {
		t.Fatalf("query index columns %s: %v", name, err)
	}
	if got != want {
		t.Errorf("index %s columns = %q, want %q", name, got, want)
	}
}

func assertSchemaVersion(t *testing.T, db *sql.DB, want string) {
	t.Helper()
	got, err := SchemaVersion(t.Context(), db)
	if err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Errorf("schema version = %q, want %q", got, want)
	}
}

func assertSingleVersionMarker(t *testing.T, db *sql.DB) {
	t.Helper()
	var count int
	if err := db.QueryRowContext(t.Context(), `SELECT count(*) FROM alembic_version`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Errorf("alembic_version marker count = %d, want 1", count)
	}
}
