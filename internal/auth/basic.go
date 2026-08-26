// Package auth provides shared authentication helpers for Go services.
package auth

import (
	"database/sql"
	"net/http"
	"strings"
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

// BasicAuthenticator adapts HTTP Basic credentials to a credential verifier.
type BasicAuthenticator struct {
	verifier Verifier
}

// NewBasicAuthenticator creates a BasicAuthenticator backed by verifier.
func NewBasicAuthenticator(verifier Verifier) *BasicAuthenticator {
	return &BasicAuthenticator{verifier: verifier}
}

// Authenticate extracts request Basic credentials and delegates verification.
//
// Result.Username is set when credentials were presented, even if they did not
// validate. Callers can distinguish missing credentials from failed credentials.
func (a *BasicAuthenticator) Authenticate(r *http.Request) Result {
	basicPresented := hasBasicAuthorizationHeader(r.Header.Get("Authorization"))
	username, password, presented := r.BasicAuth()
	if !presented {
		if basicPresented {
			return Result{Presented: true}
		}
		return Result{}
	}

	if a == nil || a.verifier == nil {
		return Result{Username: username, Presented: true}
	}

	return a.verifier.Verify(r.Context(), Credentials{Username: username, Secret: password})
}

func hasBasicAuthorizationHeader(authHeader string) bool {
	fields := strings.Fields(authHeader)
	return len(fields) > 0 && strings.EqualFold(fields[0], "Basic")
}
