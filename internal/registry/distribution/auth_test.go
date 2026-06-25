package distribution

import (
	"database/sql"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"golang.org/x/crypto/bcrypt"

	"github.com/distribution/distribution/v3/registry/auth"
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
		enabled INTEGER NOT NULL DEFAULT 1
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
	_, err = db.ExecContext(ctx, `INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`)
	if err != nil {
		t.Fatalf("insert visibility: %v", err)
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

	return db
}

func newTestController(t *testing.T, db *sql.DB) auth.AccessController {
	t.Helper()
	return newTestControllerWithAnonymousAccess(t, db, true)
}

func newTestControllerWithAnonymousAccess(t *testing.T, db *sql.DB, anonymousAccess bool) auth.AccessController {
	t.Helper()
	ac, err := newAccessController(map[string]interface{}{
		"realm":           "test-realm",
		"db":              db,
		"anonymousAccess": anonymousAccess,
	})
	if err != nil {
		t.Fatalf("new access controller: %v", err)
	}
	return ac
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
