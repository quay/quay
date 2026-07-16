package dbcore

import (
	"bytes"
	"database/sql"
	"fmt"
	"os"
	"strings"
	"testing"
)

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

func TestApplyMigrations_UserEmailBackfillAllowsDuplicateOrganizationEmails(t *testing.T) {
	db := openBridgeFixture(t, "sqlite_c3d4e5f6a7b8_minimal.sql")
	ctx := t.Context()

	if _, err := db.ExecContext(ctx, `
		UPDATE organizationcontactemail
		SET contact_email = 'shared@example.com'
		WHERE organization_id IN (1, 4)
	`); err != nil {
		t.Fatalf("set shared organization contact email: %v", err)
	}

	if err := ApplyMigrations(ctx, db, BridgeTargetVersion, "b1a79fa8e630", &bytes.Buffer{}); err != nil {
		t.Fatalf("apply user email migration: %v", err)
	}

	var count int
	if err := db.QueryRowContext(ctx, `
		SELECT count(*)
		FROM "user"
		WHERE organization = true AND email = 'shared@example.com'
	`).Scan(&count); err != nil {
		t.Fatalf("count organizations with shared email: %v", err)
	}
	if count != 2 {
		t.Fatalf("organizations with shared email = %d, want 2", count)
	}
}

func TestRunBridge_ResumesFromAlembicRevisions(t *testing.T) {
	for _, tt := range []struct {
		revision       string
		remainingCount int
	}{
		{revision: "b1a79fa8e630", remainingCount: 5},
		{revision: "d064a4f00d4a", remainingCount: 4},
		{revision: "b30800b1d271", remainingCount: 3},
		{revision: "6715e4719375", remainingCount: 2},
		{revision: generatedSchemaVersion, remainingCount: 1},
	} {
		t.Run(tt.revision, func(t *testing.T) {
			db := openBridgeFixture(t, "sqlite_c3d4e5f6a7b8_minimal.sql")
			if err := ApplyMigrations(
				t.Context(), db, BridgeTargetVersion, tt.revision, &bytes.Buffer{},
			); err != nil {
				t.Fatalf("prepare revision %s: %v", tt.revision, err)
			}

			var output bytes.Buffer
			if err := RunBridge(t.Context(), db, &output); err != nil {
				t.Fatalf("RunBridge from %s: %v", tt.revision, err)
			}
			wantCount := fmt.Sprintf("Found %d migration file(s)", tt.remainingCount)
			if !strings.Contains(output.String(), wantCount) {
				t.Fatalf("RunBridge from %s output missing %q:\n%s", tt.revision, wantCount, output.String())
			}

			assertBridgeSchemaConverged(t, db)
			assertSchemaVersion(t, db, TargetVersion)
			assertSingleVersionMarker(t, db)
		})
	}
}

func TestAlembicRevisionsAreChainableMigrations(t *testing.T) {
	catalog, err := loadEmbeddedMigrationCatalog()
	if err != nil {
		t.Fatal(err)
	}
	for _, revision := range []string{
		"c3d4e5f6a7b8",
		"b1a79fa8e630",
		"d064a4f00d4a",
		"b30800b1d271",
		"6715e4719375",
		generatedSchemaVersion,
	} {
		if _, ok := catalog.migrationsByRevision[revision]; !ok {
			t.Errorf("migration catalog is missing Alembic revision %s", revision)
		}
		if knownOMRVersions[revision] {
			t.Errorf("Alembic revision %s should route through the migration catalog", revision)
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
		{name: "created", wantType: "DATETIME"},
		{name: "last_accessed", wantType: "DATETIME"},
		{name: "display_name", wantType: "VARCHAR(255)"},
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

	for _, table := range []string{"namespacenotification", "quotanotificationstate"} {
		var count int
		if err := db.QueryRowContext(ctx,
			`SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = ?`, table,
		).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 1 {
			t.Errorf("table %s count = %d, want 1", table, count)
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
			t.Errorf("externalnotificationevent %q count = %d, want 1", event, count)
		}
	}

	for _, kind := range []string{
		"create_oauth_api_token",
		"revoke_oauth_api_token",
		"create_namespace_notification",
		"delete_namespace_notification",
		"reset_namespace_notification",
	} {
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
