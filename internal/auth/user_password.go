package auth

import (
	"context"
	"database/sql"
	"log/slog"
	"time"

	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
)

type userPasswordVerifier struct {
	queries *daldb.Queries
	// compare is bcrypt.CompareHashAndPassword; tests substitute it to count
	// how often the expensive comparison runs.
	compare func(hashedPassword, password []byte) error
	cache   *credentialCache
}

// NewUserPasswordVerifier creates a verifier for regular Quay user passwords
// that remembers successful verifications for DefaultPasswordCacheTTL.
func NewUserPasswordVerifier(db *sql.DB) Verifier {
	return NewUserPasswordVerifierWithCacheTTL(db, DefaultPasswordCacheTTL)
}

// NewUserPasswordVerifierWithCacheTTL creates a verifier for regular Quay
// user passwords. Successful verifications are remembered for ttl so repeat
// logins with the same credentials skip the bcrypt comparison; a ttl of zero
// or less disables the cache.
func NewUserPasswordVerifierWithCacheTTL(db *sql.DB, ttl time.Duration) Verifier {
	if db == nil {
		return nil
	}
	return &userPasswordVerifier{
		queries: daldb.New(db),
		compare: bcrypt.CompareHashAndPassword,
		cache:   newCredentialCache(ttl),
	}
}

// dummyHash is a valid bcrypt hash used when the user is not found, so that
// bcrypt.CompareHashAndPassword always runs and timing is constant regardless
// of whether the username exists.
var dummyHash = []byte("$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy")

func (v *userPasswordVerifier) Verify(ctx context.Context, credentials Credentials) Result {
	username := credentials.Username
	if v == nil || v.queries == nil {
		slog.Debug("authentication failed", "username", username)
		return Result{Username: username, Presented: true}
	}

	dbUser, err := v.queries.GetUserByUsername(ctx, username)

	hashToCompare := dummyHash
	usable := err == nil && dbUser.Enabled && dbUser.PasswordHash.Valid
	if usable {
		hashToCompare = []byte(dbUser.PasswordHash.String)
		// The user row is always re-read, so a disabled account or a changed
		// password takes effect immediately even while an entry is cached.
		if v.cache.matches(username, dbUser.PasswordHash.String, credentials.Secret) {
			return v.authenticated(username, &dbUser)
		}
	}

	if v.compare(hashToCompare, []byte(credentials.Secret)) != nil || !usable {
		attrs := []any{"username", username}
		if err != nil {
			attrs = append(attrs, "err", err)
		}
		slog.Debug("authentication failed", attrs...)
		return Result{Username: username, Presented: true}
	}

	v.cache.remember(username, dbUser.PasswordHash.String, credentials.Secret)
	return v.authenticated(username, &dbUser)
}

func (v *userPasswordVerifier) authenticated(username string, dbUser *daldb.GetUserByUsernameRow) Result {
	return Result{
		Principal: Principal{
			ID:       dbUser.ID,
			UUID:     dbUser.Uuid,
			Username: dbUser.Username,
			Email:    dbUser.Email,
			Kind:     PrincipalUser,
		},
		Username:      username,
		Presented:     true,
		Authenticated: true,
	}
}
