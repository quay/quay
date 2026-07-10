package distribution

import (
	"database/sql"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"golang.org/x/crypto/bcrypt"

	"github.com/distribution/distribution/v3/registry/auth"
	"github.com/quay/quay/internal/oci"
	_ "modernc.org/sqlite"
)

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	db.SetMaxOpenConns(1)

	ctx := t.Context()

	// Create minimal user table matching Quay schema.
	_, err = db.ExecContext(ctx, `CREATE TABLE "user" (
		id INTEGER PRIMARY KEY,
		uuid VARCHAR(36),
		username VARCHAR(255) NOT NULL,
		password_hash VARCHAR(255),
		email VARCHAR(255) NOT NULL,
		verified INTEGER NOT NULL DEFAULT 0,
		organization INTEGER NOT NULL DEFAULT 0,
		robot INTEGER NOT NULL DEFAULT 0,
		enabled INTEGER NOT NULL DEFAULT 1,
		last_accessed DATETIME
	)`)
	if err != nil {
		t.Fatalf("create table: %v", err)
	}

	_, err = db.ExecContext(ctx, `CREATE TABLE visibility (
		id INTEGER PRIMARY KEY,
		name VARCHAR(255) NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create visibility table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE repository (
		id INTEGER PRIMARY KEY,
		namespace_user_id INTEGER,
		name VARCHAR(255) NOT NULL,
		visibility_id INTEGER NOT NULL,
		kind_id INTEGER NOT NULL DEFAULT 1,
		state INTEGER NOT NULL DEFAULT 0
	)`)
	if err != nil {
		t.Fatalf("create repository table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE role (
		id INTEGER PRIMARY KEY,
		name VARCHAR(255) NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create role table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE teamrole (
		id INTEGER PRIMARY KEY,
		name VARCHAR(255) NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create teamrole table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE team (
		id INTEGER PRIMARY KEY,
		name VARCHAR(255) NOT NULL,
		organization_id INTEGER NOT NULL,
		role_id INTEGER NOT NULL,
		description TEXT NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create team table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE teammember (
		id INTEGER PRIMARY KEY,
		user_id INTEGER NOT NULL,
		team_id INTEGER NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create teammember table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE repositorypermission (
		id INTEGER PRIMARY KEY,
		team_id INTEGER,
		user_id INTEGER,
		repository_id INTEGER NOT NULL,
		role_id INTEGER NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create repositorypermission table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE repomirrorconfig (
		id INTEGER PRIMARY KEY,
		repository_id INTEGER NOT NULL,
		internal_robot_id INTEGER
	)`)
	if err != nil {
		t.Fatalf("create repomirrorconfig table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE orgmirrorconfig (
		id INTEGER PRIMARY KEY,
		organization_id INTEGER NOT NULL,
		internal_robot_id INTEGER
	)`)
	if err != nil {
		t.Fatalf("create orgmirrorconfig table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE orgmirrorrepository (
		id INTEGER PRIMARY KEY,
		org_mirror_config_id INTEGER NOT NULL,
		repository_id INTEGER
	)`)
	if err != nil {
		t.Fatalf("create orgmirrorrepository table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE robotaccounttoken (
		id INTEGER PRIMARY KEY,
		robot_account_id INTEGER NOT NULL,
		token VARCHAR(255) NOT NULL,
		fully_migrated BOOLEAN DEFAULT 0 NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create robotaccounttoken table: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`)
	if err != nil {
		t.Fatalf("insert visibility: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO role (id, name) VALUES (1, 'read'), (2, 'write'), (3, 'admin')`)
	if err != nil {
		t.Fatalf("insert roles: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO teamrole (id, name) VALUES (1, 'admin'), (2, 'creator'), (3, 'member')`)
	if err != nil {
		t.Fatalf("insert teamroles: %v", err)
	}

	hash, err := bcrypt.GenerateFromPassword([]byte("correct-password"), bcrypt.MinCost)
	if err != nil {
		t.Fatalf("bcrypt: %v", err)
	}

	// Active user.
	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('u1', 'admin', ?, 'admin@test.com', 1, 0, 0, 1)`, string(hash))
	if err != nil {
		t.Fatalf("insert admin: %v", err)
	}

	// Disabled user.
	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('u2', 'disabled', ?, 'disabled@test.com', 1, 0, 0, 0)`, string(hash))
	if err != nil {
		t.Fatalf("insert disabled: %v", err)
	}

	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('org-1', 'acme', NULL, 'acme@example.com', 1, 1, 0, 1)`)
	if err != nil {
		t.Fatalf("insert acme org: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('robot-read', 'acme+reader', NULL, 'robot@example.com', 1, 0, 1, 1)`)
	if err != nil {
		t.Fatalf("insert reader robot: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('robot-write', 'acme+writer', NULL, 'robot@example.com', 1, 0, 1, 1)`)
	if err != nil {
		t.Fatalf("insert writer robot: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('disabled-org', 'disabled-org', NULL, 'disabled-org@example.com', 1, 1, 0, 0)`)
	if err != nil {
		t.Fatalf("insert disabled org: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('disabled-creator', 'disabled-org+creator', NULL, 'robot@example.com', 1, 0, 1, 1)`)
	if err != nil {
		t.Fatalf("insert disabled org creator robot: %v", err)
	}

	for _, username := range []string{"public", "devtable", "library"} {
		_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
			VALUES (?, ?, NULL, ?, 1, 0, 0, 1)`, "u-"+username, username, username+"@test.com")
		if err != nil {
			t.Fatalf("insert namespace %s: %v", username, err)
		}
	}

	_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
		SELECT id, 'publicrepo', 1, 1, 0 FROM "user" WHERE username = 'public'`)
	if err != nil {
		t.Fatalf("insert public repo: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
		SELECT id, 'simple', 2, 1, 0 FROM "user" WHERE username = 'devtable'`)
	if err != nil {
		t.Fatalf("insert private repo: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
		SELECT id, 'deleted', 1, 1, 3 FROM "user" WHERE username = 'public'`)
	if err != nil {
		t.Fatalf("insert deleted repo: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
		SELECT id, 'nginx', 1, 1, 0 FROM "user" WHERE username = 'library'`)
	if err != nil {
		t.Fatalf("insert library repo: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
		SELECT id, 'private', 2, 1, 0 FROM "user" WHERE username = 'acme'`)
	if err != nil {
		t.Fatalf("insert acme private repo: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
		SELECT id, 'publicrepo', 1, 1, 0 FROM "user" WHERE username = 'disabled-org'`)
	if err != nil {
		t.Fatalf("insert disabled org public repo: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO robotaccounttoken (robot_account_id, token, fully_migrated)
		SELECT id, 'v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==', 1 FROM "user" WHERE username = 'acme+reader'`)
	if err != nil {
		t.Fatalf("insert reader robot token: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO robotaccounttoken (robot_account_id, token, fully_migrated)
		SELECT id, 'v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==', 1 FROM "user" WHERE username = 'acme+writer'`)
	if err != nil {
		t.Fatalf("insert writer robot token: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO robotaccounttoken (robot_account_id, token, fully_migrated)
		SELECT id, 'v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==', 1 FROM "user" WHERE username = 'disabled-org+creator'`)
	if err != nil {
		t.Fatalf("insert disabled org creator token: %v", err)
	}

	return db
}

func newTestController(t *testing.T, db *sql.DB) auth.AccessController {
	t.Helper()
	return newTestControllerWithAnonymousAccess(t, db, true)
}

func newTestControllerWithAnonymousAccess(t *testing.T, db *sql.DB, anonymousAccess bool) auth.AccessController {
	t.Helper()
	ac, err := newAccessController(map[string]interface{}{
		authOptionRealm:      "test-realm",
		"db":                 db,
		authOptionAnonAccess: anonymousAccess,
	})
	if err != nil {
		t.Fatalf("new access controller: %v", err)
	}
	return ac
}

func newTestControllerWithRobotAuth(t *testing.T, db *sql.DB) auth.AccessController {
	t.Helper()
	ac, err := newAccessController(map[string]interface{}{
		authOptionRealm:                      "test-realm",
		"db":                                 db,
		authOptionAnonAccess:                 true,
		"databaseSecretKey":                  "test1234",
		"featureUserLastAccessed":            true,
		"lastAccessedUpdateThresholdSeconds": 0,
	})
	if err != nil {
		t.Fatalf("new access controller: %v", err)
	}
	return ac
}

func newTestControllerWithSuperUserFullAccess(t *testing.T, db *sql.DB) auth.AccessController {
	t.Helper()
	ac, err := newAccessController(map[string]interface{}{
		authOptionRealm:        "test-realm",
		"db":                   db,
		authOptionAnonAccess:   true,
		"superUsers":           []string{"admin"},
		"superUsersFullAccess": true,
	})
	if err != nil {
		t.Fatalf("new access controller: %v", err)
	}
	return ac
}

func seedRobotPermission(t *testing.T, db *sql.DB, robotUsername, roleName string) {
	t.Helper()
	ctx := t.Context()

	var userID int64
	err := db.QueryRowContext(ctx, `SELECT id FROM "user" WHERE username = ?`, robotUsername).Scan(&userID)
	if err != nil {
		t.Fatalf("find robot user %s: %v", robotUsername, err)
	}

	var repoID int64
	err = db.QueryRowContext(ctx, `SELECT r.id
		FROM repository r
		JOIN "user" u ON r.namespace_user_id = u.id
		WHERE u.username = 'acme' AND r.name = 'private'`).Scan(&repoID)
	if err != nil {
		t.Fatalf("find repository acme/private: %v", err)
	}

	var roleID int64
	err = db.QueryRowContext(ctx, `SELECT id FROM role WHERE name = ?`, roleName).Scan(&roleID)
	if err != nil {
		t.Fatalf("find role %s: %v", roleName, err)
	}

	_, err = db.ExecContext(ctx, `INSERT INTO repositorypermission (team_id, user_id, repository_id, role_id)
		VALUES (NULL, ?, ?, ?)`, userID, repoID, roleID)
	if err != nil {
		t.Fatalf("insert robot permission: %v", err)
	}
}

func seedNamespaceTeamMembership(t *testing.T, db *sql.DB, username, namespace, teamRole string) {
	t.Helper()
	ctx := t.Context()

	var userID int64
	err := db.QueryRowContext(ctx, `SELECT id FROM "user" WHERE username = ?`, username).Scan(&userID)
	if err != nil {
		t.Fatalf("find user %s: %v", username, err)
	}

	var namespaceID int64
	err = db.QueryRowContext(ctx, `SELECT id FROM "user" WHERE username = ?`, namespace).Scan(&namespaceID)
	if err != nil {
		t.Fatalf("find namespace %s: %v", namespace, err)
	}

	var roleID int64
	err = db.QueryRowContext(ctx, `SELECT id FROM teamrole WHERE name = ?`, teamRole).Scan(&roleID)
	if err != nil {
		t.Fatalf("find team role %s: %v", teamRole, err)
	}

	result, err := db.ExecContext(ctx, `INSERT INTO team (name, organization_id, role_id, description)
		VALUES (?, ?, ?, '')`, username+"-"+teamRole, namespaceID, roleID)
	if err != nil {
		t.Fatalf("insert team: %v", err)
	}

	teamID, err := result.LastInsertId()
	if err != nil {
		t.Fatalf("team id: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO teammember (user_id, team_id) VALUES (?, ?)`, userID, teamID)
	if err != nil {
		t.Fatalf("insert team member: %v", err)
	}
}

func TestAuthorized_ValidCredentials(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	grant, err := ac.Authorized(req)
	if err != nil {
		t.Fatalf("expected success, got: %v", err)
	}
	if grant.User.Name != "admin" {
		t.Errorf("expected user 'admin', got %q", grant.User.Name)
	}
}

func TestAuthorized_WrongPassword(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/", http.NoBody)
	req.SetBasicAuth("admin", "wrong-password")

	_, err := ac.Authorized(req)
	if err == nil {
		t.Fatal("expected error for wrong password")
	}
	assertChallenge(t, err)
}

func TestAuthorized_UnknownUser(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/", http.NoBody)
	req.SetBasicAuth("nobody", "password")

	_, err := ac.Authorized(req)
	if err == nil {
		t.Fatal("expected error for unknown user")
	}
	assertChallenge(t, err)
}

func TestAuthorized_DisabledUser(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/", http.NoBody)
	req.SetBasicAuth("disabled", "correct-password")

	_, err := ac.Authorized(req)
	if err == nil {
		t.Fatal("expected error for disabled user")
	}
	assertChallenge(t, err)
}

func TestAuthorized_NoAuthHeader(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/", http.NoBody)
	// No BasicAuth set.

	_, err := ac.Authorized(req)
	if err == nil {
		t.Fatal("expected error for missing auth")
	}
	var ch auth.Challenge
	if !errors.As(err, &ch) {
		t.Fatalf("expected Challenge error, got %T", err)
	}
	// Verify the challenge sets WWW-Authenticate header.
	w := httptest.NewRecorder()
	ch.SetHeaders(req, w)
	if got := w.Header().Get("WWW-Authenticate"); got == "" {
		t.Error("expected WWW-Authenticate header")
	}
}

func TestAuthorized_AnonymousPullPublicRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/public/publicrepo/manifests/latest", http.NoBody)

	grant, err := ac.Authorized(req, repositoryAccess("public/publicrepo", "pull"))
	if err != nil {
		t.Fatalf("expected anonymous pull to public repo to succeed, got: %v", err)
	}
	if grant.User.Name != "anonymous" {
		t.Errorf("expected anonymous user, got %q", grant.User.Name)
	}
}

func TestAuthorized_AnonymousPullDisabledByFeatureFlag(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestControllerWithAnonymousAccess(t, db, false)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/public/publicrepo/manifests/latest", http.NoBody)

	_, err := ac.Authorized(req, repositoryAccess("public/publicrepo", "pull"))
	if err == nil {
		t.Fatal("expected missing auth challenge when anonymous access is disabled")
	}
	assertChallenge(t, err)
}

func TestAuthorized_AnonymousPullPrivateRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/devtable/simple/manifests/latest", http.NoBody)

	_, err := ac.Authorized(req, repositoryAccess("devtable/simple", "pull"))
	if err == nil {
		t.Fatal("expected missing auth challenge for private repo")
	}
	assertChallenge(t, err)
}

func TestAuthorized_AnonymousPullDeletedPublicRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/public/deleted/manifests/latest", http.NoBody)

	_, err := ac.Authorized(req, repositoryAccess("public/deleted", "pull"))
	if err == nil {
		t.Fatal("expected missing auth challenge for deleted public repo")
	}
	assertChallenge(t, err)
}

func TestAuthorized_AnonymousPushPublicRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/public/publicrepo/manifests/latest", http.NoBody)

	_, err := ac.Authorized(
		req,
		repositoryAccess("public/publicrepo", "pull"),
		repositoryAccess("public/publicrepo", "push"),
	)
	if err == nil {
		t.Fatal("expected missing auth challenge for anonymous push")
	}
	assertChallenge(t, err)
}

func TestAuthorized_InvalidBasicAuthDoesNotFallBackToAnonymous(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/public/publicrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "wrong-password")

	_, err := ac.Authorized(req, repositoryAccess("public/publicrepo", "pull"))
	if err == nil {
		t.Fatal("expected auth failure for invalid basic credentials")
	}
	assertChallenge(t, err)
}

func TestAuthorized_AuthenticatedUserCanPullPublicRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/public/publicrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	grant, err := ac.Authorized(req, repositoryAccess("public/publicrepo", "pull"))
	if err != nil {
		t.Fatalf("expected authenticated public pull to succeed, got: %v", err)
	}
	if grant.User.Name != "admin" {
		t.Errorf("expected grant user 'admin', got %q", grant.User.Name)
	}
}

func TestAuthorized_AnonymousPullLibraryRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/nginx/manifests/latest", http.NoBody)

	grant, err := ac.Authorized(req, repositoryAccess("nginx", "pull"))
	if err != nil {
		t.Fatalf("expected anonymous pull to library repo to succeed, got: %v", err)
	}
	if grant.User.Name != "anonymous" {
		t.Errorf("expected anonymous user, got %q", grant.User.Name)
	}
}

func TestAuthorized_RobotCreatorCanPushNewRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedNamespaceTeamMembership(t, db, "acme+writer", "acme", "creator")
	ac := newTestControllerWithRobotAuth(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/newrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+writer", "hello world")

	grant, err := ac.Authorized(
		req,
		repositoryAccess("acme/newrepo", "pull"),
		repositoryAccess("acme/newrepo", "push"),
	)
	if err != nil {
		t.Fatalf("expected creator robot push to new repository to succeed, got: %v", err)
	}
	if grant.User.Name != "acme+writer" {
		t.Errorf("expected grant user 'acme+writer', got %q", grant.User.Name)
	}
}

func TestAuthorized_NamespaceOwnerCanCheckMissingRepositoryBlobBeforePush(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "HEAD", "/v2/admin/newrepo/blobs/sha256:abc", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	grant, err := ac.Authorized(req, repositoryAccess("admin/newrepo", "pull"))
	if err != nil {
		t.Fatalf("expected namespace owner missing repository blob check to succeed, got: %v", err)
	}
	if grant.User.Name != "admin" {
		t.Errorf("expected grant user 'admin', got %q", grant.User.Name)
	}
}

func TestAuthorized_RepositoryDeleteRequiresWrite(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+reader", "read")
	seedRobotPermission(t, db, "acme+writer", "write")
	ac := newTestControllerWithRobotAuth(t, db)

	readerReq := httptest.NewRequestWithContext(t.Context(), "DELETE", "/v2/acme/private/manifests/latest", http.NoBody)
	readerReq.SetBasicAuth("acme+reader", "hello world")
	_, err := ac.Authorized(readerReq, repositoryAccess("acme/private", "delete"))
	if err == nil {
		t.Fatal("expected read robot delete to fail")
	}
	assertChallenge(t, err)

	writerReq := httptest.NewRequestWithContext(t.Context(), "DELETE", "/v2/acme/private/manifests/latest", http.NoBody)
	writerReq.SetBasicAuth("acme+writer", "hello world")
	grant, err := ac.Authorized(writerReq, repositoryAccess("acme/private", "delete"))
	if err != nil {
		t.Fatalf("expected write robot delete to succeed, got: %v", err)
	}
	if grant.User.Name != "acme+writer" {
		t.Errorf("expected grant user 'acme+writer', got %q", grant.User.Name)
	}
}

func TestAuthorized_CatalogIsDeniedUntilQuayFilteredCatalogExists(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/_catalog", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	_, err := ac.Authorized(req, auth.Access{
		Resource: auth.Resource{Type: "registry", Name: "catalog"},
		Action:   "*",
	})
	if err == nil {
		t.Fatal("expected unfiltered distribution catalog to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_WriteRobotCannotPushReadOnlyRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+writer", "write")
	if _, err := db.ExecContext(t.Context(), `UPDATE repository SET state = 1 WHERE name = 'private' AND namespace_user_id = (SELECT id FROM "user" WHERE username = 'acme')`); err != nil {
		t.Fatalf("mark repo read-only: %v", err)
	}
	ac := newTestControllerWithRobotAuth(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/private/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+writer", "hello world")
	_, err := ac.Authorized(req, repositoryAccess("acme/private", "push"))
	if err == nil {
		t.Fatal("expected read-only repository push to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_WriteRobotCannotPushApplicationRepository(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+writer", "write")
	if _, err := db.ExecContext(t.Context(), `UPDATE repository SET kind_id = 2 WHERE name = 'private' AND namespace_user_id = (SELECT id FROM "user" WHERE username = 'acme')`); err != nil {
		t.Fatalf("mark repo application kind: %v", err)
	}
	ac := newTestControllerWithRobotAuth(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/private/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+writer", "hello world")
	_, err := ac.Authorized(req, repositoryAccess("acme/private", "push"))
	if err == nil {
		t.Fatal("expected application repository push to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_DisabledNamespacePublicPullDenied(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestController(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/disabled-org/publicrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")
	_, err := ac.Authorized(req, repositoryAccess("disabled-org/publicrepo", "pull"))
	if err == nil {
		t.Fatal("expected disabled namespace public pull to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_DisabledNamespaceCreateDenied(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedNamespaceTeamMembership(t, db, "disabled-org+creator", "disabled-org", "creator")
	ac := newTestControllerWithRobotAuth(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/disabled-org/newrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("disabled-org+creator", "hello world")
	_, err := ac.Authorized(
		req,
		repositoryAccess("disabled-org/newrepo", "pull"),
		repositoryAccess("disabled-org/newrepo", "push"),
	)
	if err == nil {
		t.Fatal("expected disabled namespace create to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_SuperUserCannotCreateInDisabledNamespace(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac := newTestControllerWithSuperUserFullAccess(t, db)

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/disabled-org/newrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")
	_, err := ac.Authorized(
		req,
		repositoryAccess("disabled-org/newrepo", "pull"),
		repositoryAccess("disabled-org/newrepo", "push"),
	)
	if err == nil {
		t.Fatal("expected superuser disabled namespace create to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_RobotReadCanPullNotPush(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+reader", "read")
	ac := newTestControllerWithRobotAuth(t, db)

	pullReq := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/acme/private/manifests/latest", http.NoBody)
	pullReq.SetBasicAuth("acme+reader", "hello world")

	grant, err := ac.Authorized(pullReq, repositoryAccess("acme/private", "pull"))
	if err != nil {
		t.Fatalf("expected robot pull to succeed, got: %v", err)
	}
	if grant.User.Name != "acme+reader" {
		t.Errorf("expected grant user 'acme+reader', got %q", grant.User.Name)
	}

	pushReq := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/private/manifests/latest", http.NoBody)
	pushReq.SetBasicAuth("acme+reader", "hello world")

	_, err = ac.Authorized(pushReq, repositoryAccess("acme/private", "push"))
	if err == nil {
		t.Fatal("expected read robot push to fail")
	}
	assertChallenge(t, err)
}

func TestAuthorized_RobotWriteCanPullAndPush(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+writer", "write")
	ac := newTestControllerWithRobotAuth(t, db)

	pullReq := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/acme/private/manifests/latest", http.NoBody)
	pullReq.SetBasicAuth("acme+writer", "hello world")

	pullGrant, err := ac.Authorized(pullReq, repositoryAccess("acme/private", "pull"))
	if err != nil {
		t.Fatalf("expected robot pull to succeed, got: %v", err)
	}
	if pullGrant.User.Name != "acme+writer" {
		t.Errorf("expected pull grant user 'acme+writer', got %q", pullGrant.User.Name)
	}

	pushReq := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/private/manifests/latest", http.NoBody)
	pushReq.SetBasicAuth("acme+writer", "hello world")

	pushGrant, err := ac.Authorized(pushReq, repositoryAccess("acme/private", "push"))
	if err != nil {
		t.Fatalf("expected robot push to succeed, got: %v", err)
	}
	if pushGrant.User.Name != "acme+writer" {
		t.Errorf("expected push grant user 'acme+writer', got %q", pushGrant.User.Name)
	}
}

func TestAuthenticate_InvalidRobotCredentialsDoNotFallBackToAnonymous(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac, ok := newTestControllerWithRobotAuth(t, db).(*accessController)
	if !ok {
		t.Fatal("expected concrete accessController")
	}

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/public/publicrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+reader", "wrong")

	_, err := ac.Authenticate(req, oci.Access{Resource: "repository:public/publicrepo", Action: "pull"})
	if err == nil {
		t.Fatal("expected auth failure for invalid robot credentials")
	}
	assertChallenge(t, err)
}

func TestAuthenticate_ValidUserCannotPullPrivateRepositoryWithoutPermission(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac, ok := newTestController(t, db).(*accessController)
	if !ok {
		t.Fatal("expected concrete accessController")
	}

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/devtable/simple/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	_, err := ac.Authenticate(req, ociRepositoryAccess("devtable/simple", repositoryPullAction))
	if err == nil {
		t.Fatal("expected valid user without pull permission to fail")
	}
	assertChallenge(t, err)
}

func TestAuthenticate_ValidUserCannotPushRepositoryWithoutPermission(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac, ok := newTestController(t, db).(*accessController)
	if !ok {
		t.Fatal("expected concrete accessController")
	}

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/public/publicrepo/manifests/latest", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	_, err := ac.Authenticate(req, ociRepositoryAccess("public/publicrepo", repositoryPushAction))
	if err == nil {
		t.Fatal("expected valid user without push permission to fail")
	}
	assertChallenge(t, err)
}

func TestAuthenticate_ValidRobotCannotPullPrivateRepositoryWithoutPermission(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	ac, ok := newTestControllerWithRobotAuth(t, db).(*accessController)
	if !ok {
		t.Fatal("expected concrete accessController")
	}

	req := httptest.NewRequestWithContext(t.Context(), "GET", "/v2/acme/private/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+reader", "hello world")

	_, err := ac.Authenticate(req, ociRepositoryAccess("acme/private", repositoryPullAction))
	if err == nil {
		t.Fatal("expected valid robot without pull permission to fail")
	}
	assertChallenge(t, err)
}

func TestAuthenticate_ValidRobotCannotPushPrivateRepositoryWithReadOnlyPermission(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+reader", "read")
	ac, ok := newTestControllerWithRobotAuth(t, db).(*accessController)
	if !ok {
		t.Fatal("expected concrete accessController")
	}

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/private/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+reader", "hello world")

	_, err := ac.Authenticate(req, ociRepositoryAccess("acme/private", repositoryPushAction))
	if err == nil {
		t.Fatal("expected valid read robot push to fail")
	}
	assertChallenge(t, err)
}

func TestAuthenticate_ValidRobotCanPushPrivateRepositoryWithWritePermission(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()
	seedRobotPermission(t, db, "acme+writer", "write")
	ac, ok := newTestControllerWithRobotAuth(t, db).(*accessController)
	if !ok {
		t.Fatal("expected concrete accessController")
	}

	req := httptest.NewRequestWithContext(t.Context(), "PUT", "/v2/acme/private/manifests/latest", http.NoBody)
	req.SetBasicAuth("acme+writer", "hello world")

	grant, err := ac.Authenticate(req, ociRepositoryAccess("acme/private", repositoryPushAction))
	if err != nil {
		t.Fatalf("expected write robot push to succeed, got: %v", err)
	}
	if grant.User.Name != "acme+writer" {
		t.Errorf("expected grant user 'acme+writer', got %q", grant.User.Name)
	}
}

func assertChallenge(t *testing.T, err error) {
	t.Helper()
	var ch auth.Challenge
	if !errors.As(err, &ch) {
		t.Errorf("expected Challenge error, got %T: %v", err, err)
	}
}

func repositoryAccess(name, action string) auth.Access {
	return auth.Access{
		Resource: auth.Resource{
			Type: "repository",
			Name: name,
		},
		Action: action,
	}
}

func ociRepositoryAccess(name, action string) oci.Access {
	return oci.Access{
		Resource: "repository:" + name,
		Action:   action,
	}
}
