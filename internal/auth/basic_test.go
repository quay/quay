package auth

import (
	"database/sql"
	"net/http"
	"net/http/httptest"
	"testing"

	"golang.org/x/crypto/bcrypt"
	_ "modernc.org/sqlite"
)

func setupAuthTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	db.SetMaxOpenConns(1)

	_, err = db.ExecContext(t.Context(), `CREATE TABLE "user" (
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

	hash, err := bcrypt.GenerateFromPassword([]byte("correct-password"), bcrypt.MinCost)
	if err != nil {
		t.Fatalf("bcrypt: %v", err)
	}
	_, err = db.ExecContext(t.Context(), `INSERT INTO "user" (uuid, username, password_hash, email, verified, organization, robot, enabled)
		VALUES ('u1', 'admin', ?, 'admin@test.com', 1, 0, 0, 1)`, string(hash))
	if err != nil {
		t.Fatalf("insert user: %v", err)
	}

	return db
}

func TestBasicAuthenticatorResult(t *testing.T) {
	db := setupAuthTestDB(t)
	defer db.Close()
	authenticator := NewBasicAuthenticator(db)

	t.Run("missing credentials", func(t *testing.T) {
		req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)

		result := authenticator.Authenticate(req)

		if result.Presented {
			t.Fatal("presented = true, want false")
		}
		if result.Authenticated {
			t.Fatal("authenticated = true, want false")
		}
	})

	t.Run("valid credentials", func(t *testing.T) {
		req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)
		req.SetBasicAuth("admin", "correct-password")

		result := authenticator.Authenticate(req)

		if !result.Presented {
			t.Fatal("presented = false, want true")
		}
		if !result.Authenticated {
			t.Fatal("authenticated = false, want true")
		}
		if result.Username != "admin" {
			t.Fatalf("username = %q, want admin", result.Username)
		}
		if result.Principal.Username != "admin" {
			t.Fatalf("principal username = %q, want admin", result.Principal.Username)
		}
		if result.Principal.Kind != PrincipalUser {
			t.Fatalf("principal kind = %q, want user", result.Principal.Kind)
		}
	})

	t.Run("invalid credentials", func(t *testing.T) {
		req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)
		req.SetBasicAuth("admin", "wrong-password")

		result := authenticator.Authenticate(req)

		if !result.Presented {
			t.Fatal("presented = false, want true")
		}
		if result.Authenticated {
			t.Fatal("authenticated = true, want false")
		}
		if result.Username != "admin" {
			t.Fatalf("username = %q, want admin", result.Username)
		}
	})

	t.Run("malformed basic credentials", func(t *testing.T) {
		req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)
		req.Header.Set("Authorization", "Basic not-base64")

		result := authenticator.Authenticate(req)

		if !result.Presented {
			t.Fatal("presented = false, want true")
		}
		if result.Authenticated {
			t.Fatal("authenticated = true, want false")
		}
		if result.Username != "" {
			t.Fatalf("username = %q, want empty", result.Username)
		}
	})
}
