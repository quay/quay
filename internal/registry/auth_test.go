package registry

import (
	"context"
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

	ctx := context.Background()

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

	return db
}

func newTestController(t *testing.T, db *sql.DB) auth.AccessController {
	t.Helper()
	ac, err := newAccessController(map[string]interface{}{
		"realm": "test-realm",
		"db":    db,
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

	req := httptest.NewRequestWithContext(context.Background(), "GET", "/v2/", http.NoBody)
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

	req := httptest.NewRequestWithContext(context.Background(), "GET", "/v2/", http.NoBody)
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

	req := httptest.NewRequestWithContext(context.Background(), "GET", "/v2/", http.NoBody)
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

	req := httptest.NewRequestWithContext(context.Background(), "GET", "/v2/", http.NoBody)
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

	req := httptest.NewRequestWithContext(context.Background(), "GET", "/v2/", http.NoBody)
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

func assertChallenge(t *testing.T, err error) {
	t.Helper()
	var ch auth.Challenge
	if !errors.As(err, &ch) {
		t.Errorf("expected Challenge error, got %T: %v", err, err)
	}
}
