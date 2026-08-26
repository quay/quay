package auth

import (
	"bytes"
	"context"
	"database/sql"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
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

type recordingVerifier struct {
	called      bool
	ctx         context.Context
	credentials Credentials
	result      Result
}

func (v *recordingVerifier) Verify(ctx context.Context, credentials Credentials) Result {
	v.called = true
	v.ctx = ctx
	v.credentials = credentials
	return v.result
}

func TestBasicAuthenticatorDelegatesParsedCredentialsToVerifier(t *testing.T) {
	verifierResult := Result{
		Principal:     Principal{ID: 17, Username: "verified-user", Kind: PrincipalUser},
		Username:      "verified-user",
		Presented:     true,
		Authenticated: true,
	}
	verifier := &recordingVerifier{result: verifierResult}
	authenticator := NewBasicAuthenticator(verifier)
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	result := authenticator.Authenticate(req)

	if !verifier.called {
		t.Fatal("verifier was not called")
	}
	if verifier.ctx != req.Context() {
		t.Fatal("verifier context does not match request context")
	}
	if verifier.credentials.Username != "admin" {
		t.Fatalf("username = %q, want admin", verifier.credentials.Username)
	}
	if verifier.credentials.Secret != "correct-password" {
		t.Fatalf("secret = %q, want correct-password", verifier.credentials.Secret)
	}
	if result != verifierResult {
		t.Fatalf("result = %#v, want %#v", result, verifierResult)
	}
}

func TestBasicAuthenticatorMissingCredentialsDoesNotCallVerifier(t *testing.T) {
	verifier := &recordingVerifier{result: Result{Authenticated: true}}
	authenticator := NewBasicAuthenticator(verifier)
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)

	result := authenticator.Authenticate(req)

	if verifier.called {
		t.Fatal("verifier was called")
	}
	if result.Presented {
		t.Fatal("presented = true, want false")
	}
	if result.Authenticated {
		t.Fatal("authenticated = true, want false")
	}
}

func TestBasicAuthenticatorMalformedBasicHeaderDoesNotCallVerifier(t *testing.T) {
	verifier := &recordingVerifier{result: Result{Authenticated: true}}
	authenticator := NewBasicAuthenticator(verifier)
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)
	req.Header.Set("Authorization", "Basic not-base64")

	result := authenticator.Authenticate(req)

	if verifier.called {
		t.Fatal("verifier was called")
	}
	if !result.Presented {
		t.Fatal("presented = false, want true")
	}
	if result.Authenticated {
		t.Fatal("authenticated = true, want false")
	}
	if result.Username != "" {
		t.Fatalf("username = %q, want empty", result.Username)
	}
}

func TestBasicAuthenticatorNilVerifierFailsAfterParsingCredentials(t *testing.T) {
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/", http.NoBody)
	req.SetBasicAuth("admin", "correct-password")

	t.Run("nil authenticator", func(t *testing.T) {
		var authenticator *BasicAuthenticator

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

	t.Run("nil verifier", func(t *testing.T) {
		authenticator := NewBasicAuthenticator(nil)

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
}

func TestUserPasswordVerifierLogsLookupErrorsOnly(t *testing.T) {
	var logs bytes.Buffer
	previousLogger := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(&logs, &slog.HandlerOptions{Level: slog.LevelDebug})))
	defer slog.SetDefault(previousLogger)

	db := setupAuthTestDB(t)
	t.Cleanup(func() { _ = db.Close() })
	verifier := NewUserPasswordVerifier(db)

	verifier.Verify(t.Context(), Credentials{Username: "admin", Secret: "wrong-password"})
	if strings.Contains(logs.String(), "err=") {
		t.Fatalf("invalid credentials log included lookup error: %s", logs.String())
	}

	logs.Reset()
	brokenDB, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open broken db: %v", err)
	}
	t.Cleanup(func() { _ = brokenDB.Close() })
	brokenDB.SetMaxOpenConns(1)

	NewUserPasswordVerifier(brokenDB).Verify(t.Context(), Credentials{Username: "admin", Secret: "wrong-password"})
	if !strings.Contains(logs.String(), "err=") {
		t.Fatalf("lookup failure log missing error: %s", logs.String())
	}
}

func TestUserPasswordVerifierResult(t *testing.T) {
	db := setupAuthTestDB(t)
	defer db.Close()
	verifier := NewUserPasswordVerifier(db)

	t.Run("valid credentials", func(t *testing.T) {
		result := verifier.Verify(t.Context(), Credentials{Username: "admin", Secret: "correct-password"})

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
		result := verifier.Verify(t.Context(), Credentials{Username: "admin", Secret: "wrong-password"})

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

	t.Run("unknown user", func(t *testing.T) {
		result := verifier.Verify(t.Context(), Credentials{Username: "unknown", Secret: "wrong-password"})

		if !result.Presented {
			t.Fatal("presented = false, want true")
		}
		if result.Authenticated {
			t.Fatal("authenticated = true, want false")
		}
		if result.Username != "unknown" {
			t.Fatalf("username = %q, want unknown", result.Username)
		}
	})
}
