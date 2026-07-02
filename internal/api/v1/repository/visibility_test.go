package repository

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strconv"
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
	_, err = db.ExecContext(ctx, `CREATE TABLE team (
		id INTEGER PRIMARY KEY,
		name VARCHAR(255) NOT NULL,
		organization_id INTEGER NOT NULL,
		role_id INTEGER NOT NULL,
		description TEXT NOT NULL DEFAULT ''
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
	_, err = db.ExecContext(ctx, `CREATE TABLE queueitem (
		id INTEGER PRIMARY KEY,
		queue_name VARCHAR(1024) NOT NULL,
		body TEXT NOT NULL,
		available_after DATETIME NOT NULL,
		available BOOLEAN NOT NULL,
		processing_expires DATETIME,
		retries_remaining INTEGER NOT NULL,
		state_id VARCHAR(255) NOT NULL
	)`)
	if err != nil {
		t.Fatalf("create queueitem table: %v", err)
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
	_, err = db.ExecContext(ctx, `INSERT INTO role (id, name) VALUES (1, 'admin'), (2, 'write'), (3, 'read')`)
	if err != nil {
		t.Fatalf("insert roles: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO teamrole (id, name) VALUES (1, 'admin'), (2, 'creator'), (3, 'member')`)
	if err != nil {
		t.Fatalf("insert team roles: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`)
	if err != nil {
		t.Fatalf("insert visibility: %v", err)
	}

	insertUser := func(username string) {
		t.Helper()
		hash, err := bcrypt.GenerateFromPassword([]byte("password"), bcrypt.MinCost)
		if err != nil {
			t.Fatalf("bcrypt: %v", err)
		}
		_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
			VALUES (?, ?, ?, ?, 1, 0, 0, 1)`, "u-"+username, username, string(hash), username+"@test.com")
		if err != nil {
			t.Fatalf("insert user %s: %v", username, err)
		}
	}
	insertUser("admin")
	insertUser("devtable")
	insertUser("directadmin")
	insertUser("orgadmin")
	insertUser("reader")
	insertUser("superadmin")
	insertUser("teamadmin")

	for _, username := range []string{"public"} {
		_, err = db.ExecContext(ctx, `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
			VALUES (?, ?, NULL, ?, 1, 0, 0, 1)`, "u-"+username, username, username+"@test.com")
		if err != nil {
			t.Fatalf("insert namespace %s: %v", username, err)
		}
	}

	insertRepo := func(namespace, name string, state int) {
		t.Helper()
		_, err = db.ExecContext(ctx, `INSERT INTO repository (namespace_user_id, name, visibility_id, kind_id, state)
			SELECT u.id, ?, v.id, 1, ? FROM "user" u, visibility v WHERE u.username = ? AND v.name = ?`,
			name, state, namespace, "private")
		if err != nil {
			t.Fatalf("insert repo %s/%s: %v", namespace, name, err)
		}
	}
	insertRepo("public", "publicrepo", 0)
	insertRepo("devtable", "repo/withslash", 0)
	insertRepo("devtable", "repo/changevisibility", 0)
	insertRepo("devtable", "deleted", 3)

	_, err = db.ExecContext(ctx, `INSERT INTO repositorypermission (user_id, repository_id, role_id)
		SELECT u.id, r.id, role.id
		FROM "user" u, repository r
		JOIN "user" ns ON r.namespace_user_id = ns.id
		JOIN role ON role.name = 'admin'
		WHERE u.username = 'directadmin' AND ns.username = 'public' AND r.name = 'publicrepo'`)
	if err != nil {
		t.Fatalf("insert direct repository permission: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO team (name, organization_id, role_id, description)
		SELECT 'repoadmins', u.id, tr.id, 'repo admins'
		FROM "user" u, teamrole tr
		WHERE u.username = 'public' AND tr.name = 'member'`)
	if err != nil {
		t.Fatalf("insert repo admin team: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO teammember (user_id, team_id)
		SELECT u.id, t.id
		FROM "user" u, team t
		WHERE u.username = 'teamadmin' AND t.name = 'repoadmins'`)
	if err != nil {
		t.Fatalf("insert repo admin team member: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO repositorypermission (team_id, repository_id, role_id)
		SELECT t.id, r.id, role.id
		FROM team t, repository r
		JOIN "user" ns ON r.namespace_user_id = ns.id
		JOIN role ON role.name = 'admin'
		WHERE t.name = 'repoadmins' AND ns.username = 'public' AND r.name = 'publicrepo'`)
	if err != nil {
		t.Fatalf("insert team repository permission: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO team (name, organization_id, role_id, description)
		SELECT 'owners', u.id, tr.id, 'owners'
		FROM "user" u, teamrole tr
		WHERE u.username = 'public' AND tr.name = 'admin'`)
	if err != nil {
		t.Fatalf("insert org admin team: %v", err)
	}
	_, err = db.ExecContext(ctx, `INSERT INTO teammember (user_id, team_id)
		SELECT u.id, t.id
		FROM "user" u, team t
		WHERE u.username = 'orgadmin' AND t.name = 'owners'`)
	if err != nil {
		t.Fatalf("insert org admin team member: %v", err)
	}
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
	return newAPITestHandlerWithSuperUsers(t, db, []string{"admin"}, true)
}

func newAPITestHandlerWithSuperUsers(t *testing.T, db *sql.DB, superUsers []string, superUsersFullAccess bool) http.Handler {
	t.Helper()
	repositoryService, err := repomodel.NewService(
		repositorydal.NewStore(db),
		repositorydal.NewAuthorizer(db, repositorydal.AuthorizerConfig{
			SuperUsers:           superUsers,
			SuperUsersFullAccess: superUsersFullAccess,
		}),
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

type staticAuthenticator struct{}

func (staticAuthenticator) Authenticate(*http.Request) auth.Result {
	return auth.Result{
		Principal:     auth.Principal{Username: "admin", Kind: auth.PrincipalUser},
		Username:      "admin",
		Presented:     true,
		Authenticated: true,
	}
}

type stubService struct {
	changeErr error
	deleteErr error
}

func (s stubService) ChangeVisibility(context.Context, *auth.Principal, repomodel.Ref, repomodel.Visibility) error {
	return s.changeErr
}

func (s stubService) Delete(context.Context, *auth.Principal, repomodel.Ref) error {
	return s.deleteErr
}

func newStubHandler(t *testing.T, service Service) http.Handler {
	t.Helper()
	handler, err := apiv1.New(apiv1.Config{
		Authenticator: staticAuthenticator{},
		Realm:         "test",
	}, NewModule(service))
	if err != nil {
		t.Fatalf("new api: %v", err)
	}
	return handler
}

func captureLogs(t *testing.T) *bytes.Buffer {
	t.Helper()
	var buf bytes.Buffer
	previous := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(&buf, nil)))
	t.Cleanup(func() {
		slog.SetDefault(previous)
	})
	return &buf
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

func TestChangeVisibilityDirectRepositoryAdminSuccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "directadmin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "public" {
		t.Fatalf("visibility = %q, want public", got)
	}
}

func TestChangeVisibilityTeamRepositoryAdminSuccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "teamadmin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "public" {
		t.Fatalf("visibility = %q, want public", got)
	}
}

func TestChangeVisibilityOrgAdminTeamSuccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "orgadmin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "public" {
		t.Fatalf("visibility = %q, want public", got)
	}
}

func TestChangeVisibilityConfiguredSuperuserSuccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandlerWithSuperUsers(t, db, []string{"superadmin"}, true)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "superadmin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "public" {
		t.Fatalf("visibility = %q, want public", got)
	}
}

func TestChangeVisibilityConfiguredSuperuserRequiresFullAccess(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandlerWithSuperUsers(t, db, []string{"superadmin"}, false)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	setBasicAuth(req, "superadmin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "private" {
		t.Fatalf("visibility = %q, want unchanged private", got)
	}
}

func TestChangeVisibilityRequestBodyTooLarge(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	body := `{"visibility":"` + strings.Repeat("x", changeVisibilityRequestMaxBytes) + `"}`
	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(body))
	setBasicAuth(req, "admin")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("status = %d, want 413", rec.Code)
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "private" {
		t.Fatalf("visibility = %q, want unchanged private", got)
	}
}

func TestChangeVisibilityUnexpectedErrorLogs(t *testing.T) {
	sentinelErr := errors.New("database unavailable")
	logs := captureLogs(t)
	handler := newStubHandler(t, stubService{changeErr: sentinelErr})

	req := httptest.NewRequestWithContext(t.Context(), http.MethodPost, "/api/v1/repository/public/publicrepo/changevisibility", strings.NewReader(`{"visibility":"public"}`))
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	logOutput := logs.String()
	if !strings.Contains(logOutput, "visibility update failed") || !strings.Contains(logOutput, sentinelErr.Error()) {
		t.Fatalf("log output = %q, want visibility update failure with underlying error", logOutput)
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

func TestSetVisibilityInvalidVisibilityNotFound(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	store := repositorydal.NewStore(db)

	repo, err := daldb.New(db).GetRepositoryAccessByNamespaceName(t.Context(), daldb.GetRepositoryAccessByNamespaceNameParams{
		Username: "public",
		Name:     "publicrepo",
	})
	if err != nil {
		t.Fatalf("lookup repository: %v", err)
	}

	err = store.SetVisibility(t.Context(), repo.ID, repomodel.Visibility("internal"))
	if !errors.Is(err, repomodel.ErrNotFound) {
		t.Fatalf("err = %v, want ErrNotFound", err)
	}
	if got := repositoryVisibility(t, db, "public", "publicrepo"); got != "private" {
		t.Fatalf("visibility = %q, want unchanged private", got)
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

func TestDeleteRepositoryOwnerSuccessWithChangeVisibilitySuffixRepository(t *testing.T) {
	db := setupAPITestDB(t)
	defer db.Close()
	handler := newAPITestHandler(t, db)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/devtable/repo/changevisibility", http.NoBody)
	setBasicAuth(req, "devtable")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	assertRepositoryDeleted(t, db, "repo/changevisibility")
}

func TestDeleteRepositoryUnexpectedErrorLogs(t *testing.T) {
	sentinelErr := errors.New("database unavailable")
	logs := captureLogs(t)
	handler := newStubHandler(t, stubService{deleteErr: sentinelErr})

	req := httptest.NewRequestWithContext(t.Context(), http.MethodDelete, "/api/v1/repository/public/publicrepo", http.NoBody)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	logOutput := logs.String()
	if !strings.Contains(logOutput, "repository delete failed") || !strings.Contains(logOutput, sentinelErr.Error()) {
		t.Fatalf("log output = %q, want repository delete failure with underlying error", logOutput)
	}
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
	var markerID int64
	var repositoryID int64
	var namespace string
	var state int
	var markedOriginalName string
	var queueID sql.NullString
	err := db.QueryRowContext(t.Context(), `SELECT d.id, r.id, ns.username, r.name, r.state, d.original_name, d.queue_id
		FROM deletedrepository d
		JOIN repository r ON d.repository_id = r.id
		JOIN "user" ns ON r.namespace_user_id = ns.id
		WHERE d.original_name = ?`, originalName).Scan(&markerID, &repositoryID, &namespace, &deletedName, &state, &markedOriginalName, &queueID)
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
	if !queueID.Valid || queueID.String == "" {
		t.Fatal("deletedrepository queue_id is empty")
	}

	queueItemID, err := strconv.ParseInt(queueID.String, 10, 64)
	if err != nil {
		t.Fatalf("deletedrepository queue_id = %q, want numeric queue item ID: %v", queueID.String, err)
	}

	var queueName string
	var body string
	var available bool
	var retriesRemaining int
	var stateID string
	err = db.QueryRowContext(t.Context(), `SELECT queue_name, body, available, retries_remaining, state_id
		FROM queueitem
		WHERE id = ?`, queueItemID).Scan(&queueName, &body, &available, &retriesRemaining, &stateID)
	if err != nil {
		t.Fatalf("lookup repository GC queue item: %v", err)
	}
	if queueName != fmt.Sprintf("repositorygc/%s/%d/", namespace, repositoryID) {
		t.Fatalf("queue_name = %q, want repositorygc/%s/%d/", queueName, namespace, repositoryID)
	}
	if !available {
		t.Fatal("queue item available = false, want true")
	}
	if retriesRemaining != 5 {
		t.Fatalf("queue item retries_remaining = %d, want 5", retriesRemaining)
	}
	if stateID == "" {
		t.Fatal("queue item state_id is empty")
	}
	var queueBody struct {
		MarkerID     int64  `json:"marker_id"`
		OriginalName string `json:"original_name"`
	}
	if err := json.Unmarshal([]byte(body), &queueBody); err != nil {
		t.Fatalf("decode queue item body: %v", err)
	}
	if queueBody.MarkerID != markerID {
		t.Fatalf("queue body marker_id = %d, want %d", queueBody.MarkerID, markerID)
	}
	if queueBody.OriginalName != originalName {
		t.Fatalf("queue body original_name = %q, want %q", queueBody.OriginalName, originalName)
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
