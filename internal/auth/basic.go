// Package auth provides shared authentication helpers for Go services.
package auth

import (
	"database/sql"
	"log/slog"
	"net/http"
	"strings"

	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
)

// PrincipalKind identifies the kind of authenticated identity.
type PrincipalKind string

const (
	// PrincipalUser is a regular user account.
	PrincipalUser PrincipalKind = "user"
	// PrincipalRobot is a robot account.
	PrincipalRobot PrincipalKind = "robot"
	// PrincipalAnonymous is an unauthenticated caller.
	PrincipalAnonymous PrincipalKind = "anonymous"
)

// Principal is the identity evaluated by API and registry authorization.
type Principal struct {
	ID       int64
	UUID     sql.NullString
	Username string
	Email    string
	Kind     PrincipalKind
}

// AnonymousPrincipal returns the shared anonymous identity.
func AnonymousPrincipal() *Principal {
	return &Principal{Username: "anonymous", Kind: PrincipalAnonymous}
}

// IsAnonymous reports whether p represents an unauthenticated caller.
func (p *Principal) IsAnonymous() bool {
	return p == nil || p.Kind == PrincipalAnonymous
}

// Result describes the outcome of an authentication attempt.
type Result struct {
	// Principal is populated only when authentication succeeds.
	Principal Principal
	// Username is populated when credentials were presented, even if they were
	// invalid. This lets callers distinguish failed credentials from missing
	// credentials without re-parsing the request.
	Username string
	// Presented reports whether the request included credentials for this
	// authenticator. For Basic auth, this means an Authorization: Basic header
	// was present; it does not imply the credentials were valid.
	Presented bool
	// Authenticated reports whether the presented credentials were valid.
	Authenticated bool
}

// BasicAuthenticator validates HTTP Basic credentials against the Quay user table.
type BasicAuthenticator struct {
	queries *daldb.Queries
}

// NewBasicAuthenticator creates a BasicAuthenticator backed by db.
func NewBasicAuthenticator(db *sql.DB) *BasicAuthenticator {
	return &BasicAuthenticator{queries: daldb.New(db)}
}

// dummyHash is a valid bcrypt hash used when the user is not found, so that
// bcrypt.CompareHashAndPassword always runs and timing is constant regardless
// of whether the username exists.
var dummyHash = []byte("$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy")

// Authenticate validates request Basic credentials.
//
// Result.Username is set when credentials were presented, even if they did not
// validate. Callers can distinguish missing credentials from failed credentials
// while preserving constant-time password comparison.
func (a *BasicAuthenticator) Authenticate(r *http.Request) Result {
	basicPresented := hasBasicAuthorizationHeader(r.Header.Get("Authorization"))
	username, password, presented := r.BasicAuth()
	if !presented {
		if basicPresented {
			return Result{Presented: true}
		}
		return Result{}
	}

	dbUser, err := a.queries.GetUserByUsername(r.Context(), username)

	hashToCompare := dummyHash
	if err == nil && dbUser.Enabled && dbUser.PasswordHash.Valid {
		hashToCompare = []byte(dbUser.PasswordHash.String)
	}

	if bcrypt.CompareHashAndPassword(hashToCompare, []byte(password)) != nil ||
		err != nil || !dbUser.Enabled || !dbUser.PasswordHash.Valid {
		slog.Debug("authentication failed", "username", username)
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

func hasBasicAuthorizationHeader(authHeader string) bool {
	fields := strings.Fields(authHeader)
	return len(fields) > 0 && strings.EqualFold(fields[0], "Basic")
}
