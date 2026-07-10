package auth

import (
	"context"
	"database/sql"
	"log/slog"

	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
)

type userPasswordVerifier struct {
	queries *daldb.Queries
}

// NewUserPasswordVerifier creates a verifier for regular Quay user passwords.
func NewUserPasswordVerifier(db *sql.DB) Verifier {
	if db == nil {
		return nil
	}
	return &userPasswordVerifier{queries: daldb.New(db)}
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
	if err == nil && dbUser.Enabled && dbUser.PasswordHash.Valid {
		hashToCompare = []byte(dbUser.PasswordHash.String)
	}

	if bcrypt.CompareHashAndPassword(hashToCompare, []byte(credentials.Secret)) != nil ||
		err != nil || !dbUser.Enabled || !dbUser.PasswordHash.Valid {
		attrs := []any{"username", username}
		if err != nil {
			attrs = append(attrs, "err", err)
		}
		slog.Debug("authentication failed", attrs...)
		return Result{Username: username, Presented: true}
	}

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
