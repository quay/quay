package repository

import (
	"database/sql"
	"encoding/base64"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"golang.org/x/crypto/bcrypt"

	apiv1 "github.com/quay/quay/internal/api/v1"
	"github.com/quay/quay/internal/auth"
	"github.com/quay/quay/internal/dal/daldb"
	repomodel "github.com/quay/quay/internal/repository"
	repositorydal "github.com/quay/quay/internal/repository/dal"
	_ "modernc.org/sqlite"
)

func setupAPITestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	db.SetMaxOpenConns(1)

	ctx := t.Context()
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
		t.Fatalf("create user table: %v", err)
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
	_, err = db.ExecContext(ctx, `CREATE TABLE deletedrepository (
		id INTEGER PRIMARY KEY,
		repository_id INTEGER NOT NULL,
		marked DATETIME NOT NULL,
		original_name VARCHAR(255) NOT NULL,
		queue_id VARCHAR(255)
	)`)
	if err != nil {
		t.Fatalf("create deletedrepository table: %v", err)
	}
	_, err = db.ExecContext(ctx, `CREATE TABLE star (
		id INTEGER PRIMARY KEY,
		user_id INTEGER NOT NULL,
		repository_id INTEGER NOT NULL,
		created DATETIME NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create star table: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`)
	if err != nil {
		t.Fatalf("insert visibility: %v", err)
	}

	insertUser := func(username, password string) {
		t.Helper()
		hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.MinCost)
		if err != nil {
			t.Fatalf("bcrypt: %v", err)
		}
		_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
			VALUES (?, ?, ?, ?, 1, 0, 0, 1)`, "u-"+username, username, string(hash), username+"@test.com")
		if err != nil {
			t.Fatalf("insert user %s: %v", username, err)
		}
	}
	insertUser("admin", "password")
	insertUser("devtable", "password")
	insertUser("reader", "password")

	for _, username := range []string{"public"} {
		_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
			VALUES (?, ?, NULL, ?, 1, 0, 0, 1)`, "u-"+username, username, username+"@test.com")
		if err != nil {
			t.Fatalf("insert namespace %s: %v", username, err)
		}
	}

	insertRepo := func(namespace, name, visibility string, state int) {
		t.Helper()
		_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
			SELECT u.id, ?, v.id, 1, ? FROM "user" u, visibility v WHERE u.username = ? AND v.name = ?`,
			name, state, namespace, visibility)
		if err != nil {
			t.Fatalf("insert repo %s/%s: %v", namespace, name, err)
		}
	}
	insertRepo("public", "publicrepo", "private", 0)
	insertRepo("devtable", "repo/withslash", "private", 0)
	insertRepo("devtable", "deleted", "private", 3)
	_, err = db.ExecContext(ctx, `INSERT INTO star (user_id, repository_id, created)
		SELECT u.id, r.id, datetime('now')
		FROM "user" u, repository r
		JOIN "user" ns ON r.namespace_user_id = ns.id
		WHERE u.username = 'reader' AND ns.username = 'public' AND r.name = 'publicrepo'`)
	if err != nil {
		t.Fatalf("insert star: %v", err)
	}

	return db
}

func newAPITestHandler(t *testing.T, db *sql.DB) http.Handler {
	t.Helper()
	repositoryService, err := repomodel.NewService(
		repositorydal.NewStore(db),
		repomodel.OwnerOrBootstrapAdminAuthorizer{AdminUsername: "admin"},
	)
	if err != nil {
		t.Fatalf("new repository service: %v", err)
	}

	handler, err := apiv1.New(apiv1.Config{
		Authenticator: auth.NewBasicAuthenticator(db),
		Realm:         "test",
	},
		NewModule(repositoryService),
	)
	if err != nil {
		t.Fatalf("new api: %v", err)
	}
	return handler
}

func TestChangeVisibilityAdminSuccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "public" {
		t.Fatalf("visibility = %q, want public", got)
	}
}

func TestChangeVisibilityOwnerSuccessWithSlashRepository(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/devtable/repo/withslash/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "devtable")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if got := repositoryVisibility(t, db, "devtable", "repo/withslash"); got != "public" {
		t.Fatalf("visibility = %q, want public", got)
	}
}

func TestChangeVisibilityRequiresAuth(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rec.Code)
	}
	if got := rec.Header().Get("WWW-Authenticate"); got == "" {
		t.Fatal("expected WWW-Authenticate header")
	}
}

func TestChangeVisibilityForbidden(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "reader")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
}

func TestChangeVisibilityInvalidVisibility(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"internal"}`))
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}

func TestChangeVisibilityMissingRepository(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/missing/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

func TestChangeVisibilityDeletedRepositoryNotFound(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/devtable/deleted/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

func TestDeleteRepositoryAdminSuccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/public/publicrepo", http.NoBody)
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	assertRepositoryDeleted(t, db, "publicrepo")
	if got := starCount(t, db); got != 0 {
		t.Fatalf("star count = %d, want 0", got)
	}
}

func TestDeleteRepositoryOwnerSuccessWithSlashRepository(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/devtable/repo/withslash", http.NoBody)
	setBasicAuth(req, "devtable")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	assertRepositoryDeleted(t, db, "repo/withslash")
}

func TestDeleteRepositoryRequiresAuth(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/public/publicrepo", http.NoBody)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rec.Code)
	}
	if got := rec.Header().Get("WWW-Authenticate"); got == "" {
		t.Fatal("expected WWW-Authenticate header")
	}
}

func TestDeleteRepositoryForbidden(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/public/publicrepo", http.NoBody)
	setBasicAuth(req, "reader")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
}

func TestDeleteRepositoryMissingRepository(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/public/missing", http.NoBody)
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

func setBasicAuth(req *http.Request, username string) {
	token := base64.StdEncoding.EncodeToString([]byte(username + ":password"))
	req.Header.Set("Authorization", "Basic "+token)
}

func repositoryVisibility(t *testing.T, db *sql.DB, namespace, repository string) string {
	t.Helper()
	q := daldb.New(db)
	repo, err := q.GetRepositoryAccessByNamespaceName(t.Context(), daldb.GetRepositoryAccessByNamespaceNameParams{
		Username: namespace,
		Name:     repository,
	})
	if err != nil {
		t.Fatalf("lookup repository: %v", err)
	}
	return repo.Visibility
}

func assertRepositoryDeleted(t *testing.T, db *sql.DB, originalName string) {
	t.Helper()

	var deletedName string
	var state int
	var markedOriginalName string
	err := db.QueryRowContext(t.Context(), `SELECT r.name, r.state, d.original_name
		FROM deletedrepository d
		JOIN repository r ON d.repository_id = r.id
		WHERE d.original_name = ?`, originalName).Scan(&deletedName, &state, &markedOriginalName)
	if err != nil {
		t.Fatalf("lookup deleted repository: %v", err)
	}
	if markedOriginalName != originalName {
		t.Fatalf("deletedrepository original_name = %q, want %q", markedOriginalName, originalName)
	}
	if state != 3 {
		t.Fatalf("repository state = %d, want 3", state)
	}
	if deletedName == originalName || deletedName == "" {
		t.Fatalf("deleted repository name = %q, want generated name", deletedName)
	}

	var activeCount int
	if err := db.QueryRowContext(t.Context(), `SELECT COUNT(*) FROM repository WHERE name = ? AND state != 3`, originalName).Scan(&activeCount); err != nil {
		t.Fatalf("count active repositories by original name: %v", err)
	}
	if activeCount != 0 {
		t.Fatalf("active repository count for original name = %d, want 0", activeCount)
	}
}

func starCount(t *testing.T, db *sql.DB) int {
	t.Helper()
	var count int
	if err := db.QueryRowContext(t.Context(), `SELECT COUNT(*) FROM star`).Scan(&count); err != nil {
		t.Fatalf("count stars: %v", err)
	}
	return count
}
