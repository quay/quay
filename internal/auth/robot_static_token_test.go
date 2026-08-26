package auth

import (
	"bytes"
	"database/sql"
	"log/slog"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"golang.org/x/crypto/bcrypt"
	_ "modernc.org/sqlite"
)

const testEncryptedRobotToken = "v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA=="

func setupRobotStaticTokenTestDB(t *testing.T) *sql.DB {
	t.Helper()

	return setupRobotStaticTokenTestDBWithDSN(t, ":memory:", 1)
}

func setupRobotStaticTokenTestDBWithDSN(t *testing.T, dsn string, maxOpenConns int) *sql.DB {
	t.Helper()

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	db.SetMaxOpenConns(maxOpenConns)

	_, err = db.ExecContext(t.Context(), `CREATE TABLE "user" (
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
		t.Fatalf("create user table: %v", err)
	}

	_, err = db.ExecContext(t.Context(), `CREATE TABLE robotaccounttoken (
		id INTEGER PRIMARY KEY,
		robot_account_id INTEGER NOT NULL,
		token TEXT NOT NULL,
		fully_migrated INTEGER NOT NULL DEFAULT 0
	)`)
	if err != nil {
		t.Fatalf("create robotaccounttoken table: %v", err)
	}

	passwordHash, err := bcrypt.GenerateFromPassword([]byte("correct-password"), bcrypt.MinCost)
	if err != nil {
		t.Fatalf("bcrypt: %v", err)
	}

	rows := []struct {
		id           int64
		uuid         string
		username     string
		passwordHash sql.NullString
		email        string
		verified     bool
		organization bool
		robot        bool
		enabled      bool
	}{
		{id: 1, uuid: "owner-acme", username: "acme", email: "acme@example.com", verified: true, organization: true, enabled: true},
		{id: 2, uuid: "robot-acme-deploy", username: "acme+deploy", email: "acme+deploy@example.com", verified: true, robot: true, enabled: true},
		{id: 3, uuid: "owner-disabledorg", username: "disabledorg", email: "disabledorg@example.com", verified: true, organization: true, enabled: false},
		{id: 4, uuid: "robot-disabledorg-deploy", username: "disabledorg+deploy", email: "disabledorg+deploy@example.com", verified: true, robot: true, enabled: true},
		{id: 5, uuid: "robot-acme-disabled", username: "acme+disabled", email: "acme+disabled@example.com", verified: true, robot: true, enabled: false},
		{id: 6, uuid: "robot-missing", username: "missing+robot", email: "missing+robot@example.com", verified: true, robot: true, enabled: true},
		{id: 7, uuid: "user-admin", username: "admin", passwordHash: sql.NullString{String: string(passwordHash), Valid: true}, email: "admin@example.com", verified: true, enabled: true},
	}
	for _, row := range rows {
		_, err = db.ExecContext(
			t.Context(),
			`INSERT INTO "user" (id, uuid, username, password_hash, email, verified, organization, robot, enabled)
			 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			row.id,
			row.uuid,
			row.username,
			row.passwordHash,
			row.email,
			row.verified,
			row.organization,
			row.robot,
			row.enabled,
		)
		if err != nil {
			t.Fatalf("insert user %q: %v", row.username, err)
		}
	}

	tokenRows := []struct {
		id      int64
		robotID int64
	}{
		{id: 1, robotID: 2},
		{id: 2, robotID: 4},
		{id: 3, robotID: 5},
		{id: 4, robotID: 6},
	}
	for _, row := range tokenRows {
		_, err = db.ExecContext(
			t.Context(),
			`INSERT INTO robotaccounttoken (id, robot_account_id, token, fully_migrated)
			 VALUES (?, ?, ?, 0)`,
			row.id,
			row.robotID,
			testEncryptedRobotToken,
		)
		if err != nil {
			t.Fatalf("insert token for robot %d: %v", row.robotID, err)
		}
	}

	return db
}

func TestDatabaseVerifierStaticRobotToken(t *testing.T) {
	db := setupRobotStaticTokenTestDB(t)
	defer db.Close()

	verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{
		DatabaseSecretKey:              "test1234",
		FeatureUserLastAccessed:        true,
		LastAccessedUpdateThresholdSec: 0,
	})

	result := verifier.Verify(t.Context(), Credentials{Username: "acme+deploy", Secret: "hello world"})

	if !result.Presented {
		t.Fatal("presented = false, want true")
	}
	if !result.Authenticated {
		t.Fatal("authenticated = false, want true")
	}
	if result.Username != "acme+deploy" {
		t.Fatalf("username = %q, want acme+deploy", result.Username)
	}
	if result.Principal.Username != "acme+deploy" {
		t.Fatalf("principal username = %q, want acme+deploy", result.Principal.Username)
	}
	if result.Principal.Kind != PrincipalRobot {
		t.Fatalf("principal kind = %q, want robot", result.Principal.Kind)
	}
}

func TestDatabaseVerifierRoutesRegularUsers(t *testing.T) {
	db := setupRobotStaticTokenTestDB(t)
	defer db.Close()

	verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{DatabaseSecretKey: "test1234"})

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
}

func TestDatabaseVerifierRobotFailures(t *testing.T) {
	tests := []struct {
		name     string
		cfg      DatabaseVerifierConfig
		username string
		secret   string
	}{
		{
			name:     "wrong token",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "test1234"},
			username: "acme+deploy",
			secret:   "wrong",
		},
		{
			name:     "wrong key",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "wrong-key"},
			username: "acme+deploy",
			secret:   "hello world",
		},
		{
			name:     "empty key",
			cfg:      DatabaseVerifierConfig{},
			username: "acme+deploy",
			secret:   "hello world",
		},
		{
			name:     "disabled robot",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "test1234"},
			username: "acme+disabled",
			secret:   "hello world",
		},
		{
			name:     "orphan robot",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "test1234"},
			username: "missing+robot",
			secret:   "hello world",
		},
		{
			name:     "disabled owner",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "test1234"},
			username: "disabledorg+deploy",
			secret:   "hello world",
		},
		{
			name:     "non-ASCII secret",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "test1234"},
			username: "acme+deploy",
			secret:   "hello worldé",
		},
		{
			name:     "JWT-shaped wrong secret",
			cfg:      DatabaseVerifierConfig{DatabaseSecretKey: "test1234"},
			username: "acme+deploy",
			secret:   "a.b.c",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			db := setupRobotStaticTokenTestDB(t)
			defer db.Close()

			verifier := NewDatabaseVerifier(db, tt.cfg)
			result := verifier.Verify(t.Context(), Credentials{Username: tt.username, Secret: tt.secret})

			if !result.Presented {
				t.Fatal("presented = false, want true")
			}
			if result.Authenticated {
				t.Fatal("authenticated = true, want false")
			}
			if result.Username != tt.username {
				t.Fatalf("username = %q, want %q", result.Username, tt.username)
			}
		})
	}
}

func TestDatabaseVerifierRobotsDisallowWhitelist(t *testing.T) {
	t.Run("non-whitelisted robot denied", func(t *testing.T) {
		db := setupRobotStaticTokenTestDB(t)
		defer db.Close()

		verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{
			DatabaseSecretKey: "test1234",
			RobotsDisallow:    true,
		})
		result := verifier.Verify(t.Context(), Credentials{Username: "acme+deploy", Secret: "hello world"})

		if !result.Presented {
			t.Fatal("presented = false, want true")
		}
		if result.Authenticated {
			t.Fatal("authenticated = true, want false")
		}
	})

	t.Run("whitelisted robot accepted", func(t *testing.T) {
		db := setupRobotStaticTokenTestDB(t)
		defer db.Close()

		verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{
			DatabaseSecretKey: "test1234",
			RobotsDisallow:    true,
			RobotsWhitelist:   []string{"acme+deploy"},
		})
		result := verifier.Verify(t.Context(), Credentials{Username: "acme+deploy", Secret: "hello world"})

		if !result.Presented {
			t.Fatal("presented = false, want true")
		}
		if !result.Authenticated {
			t.Fatal("authenticated = false, want true")
		}
		if result.Principal.Kind != PrincipalRobot {
			t.Fatalf("principal kind = %q, want robot", result.Principal.Kind)
		}
	})
}

func TestStaticRobotTokenUpdatesLastAccessed(t *testing.T) {
	db := setupRobotStaticTokenTestDB(t)
	defer db.Close()

	verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{
		DatabaseSecretKey:              "test1234",
		FeatureUserLastAccessed:        true,
		LastAccessedUpdateThresholdSec: 0,
	})

	result := verifier.Verify(t.Context(), Credentials{Username: "acme+deploy", Secret: "hello world"})
	if !result.Authenticated {
		t.Fatal("authenticated = false, want true")
	}

	var lastAccessed sql.NullString
	if err := db.QueryRowContext(t.Context(), `SELECT last_accessed FROM "user" WHERE username = ?`, "acme+deploy").Scan(&lastAccessed); err != nil {
		t.Fatalf("select last_accessed: %v", err)
	}
	if !lastAccessed.Valid {
		t.Fatal("last_accessed is NULL, want timestamp")
	}
}

func TestStaticRobotTokenSkipsFreshLastAccessedUpdate(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "robots.db")
	dsn := "file:" + dbPath + "?_pragma=journal_mode(WAL)&_pragma=busy_timeout(1)"
	db := setupRobotStaticTokenTestDBWithDSN(t, dsn, 5)
	defer db.Close()

	freshLastAccessed := time.Now().UTC()
	if _, err := db.ExecContext(t.Context(), `UPDATE "user" SET last_accessed = ? WHERE username = ?`, freshLastAccessed, "acme+deploy"); err != nil {
		t.Fatalf("seed last_accessed: %v", err)
	}

	lockDB, err := sql.Open("sqlite", dsn)
	if err != nil {
		t.Fatalf("open lock db: %v", err)
	}
	defer lockDB.Close()

	lockConn, err := lockDB.Conn(t.Context())
	if err != nil {
		t.Fatalf("open lock conn: %v", err)
	}
	defer lockConn.Close()
	if _, err := lockConn.ExecContext(t.Context(), `BEGIN IMMEDIATE`); err != nil {
		t.Fatalf("begin lock transaction: %v", err)
	}
	defer lockConn.ExecContext(t.Context(), `ROLLBACK`)

	var logs bytes.Buffer
	previousLogger := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(&logs, &slog.HandlerOptions{Level: slog.LevelDebug})))
	defer slog.SetDefault(previousLogger)

	verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{
		DatabaseSecretKey:              "test1234",
		FeatureUserLastAccessed:        true,
		LastAccessedUpdateThresholdSec: int((1 * time.Hour).Seconds()),
	})

	result := verifier.Verify(t.Context(), Credentials{Username: "acme+deploy", Secret: "hello world"})
	if !result.Authenticated {
		t.Fatal("authenticated = false, want true")
	}
	if strings.Contains(logs.String(), "robot last_accessed update failed") {
		t.Fatalf("fresh last_accessed attempted update under write lock: %s", logs.String())
	}
}

func TestStaticRobotTokenConcurrentAuth(t *testing.T) {
	db := setupRobotStaticTokenTestDB(t)
	defer db.Close()

	verifier := NewDatabaseVerifier(db, DatabaseVerifierConfig{DatabaseSecretKey: "test1234"})

	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()

			result := verifier.Verify(t.Context(), Credentials{Username: "acme+deploy", Secret: "hello world"})
			if !result.Authenticated {
				t.Errorf("authenticated = false, want true")
			}
			if result.Principal.Kind != PrincipalRobot {
				t.Errorf("principal kind = %q, want robot", result.Principal.Kind)
			}
		}()
	}
	wg.Wait()
}
