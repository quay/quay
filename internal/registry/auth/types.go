// Package auth implements the Docker Registry v2 bearer-token flow.
//
// It is intentionally a leaf package: callers adapt credential verification
// and repository authorization through the function types defined here.
package auth

import (
	"context"

	"github.com/go-jose/go-jose/v4/jwt"
)

const (
	// AnonymousSubject matches the subject used by Python Quay registry tokens.
	AnonymousSubject = "(anonymous)"
	// Issuer is the issuer used for Go OMR registry tokens.
	Issuer = "quay"
)

// Identity is the authenticated identity presented to a GrantResolver.
// Principal is opaque to this leaf package and lets the composition root carry
// its authorization-domain identity without coupling packages.
type Identity struct {
	Subject   string
	Principal any
	Anonymous bool
}

// AuthenticateFunc validates a username and secret.
// Invalid credentials return ok=false; transport and authorization remain
// separate from credential validation.
type AuthenticateFunc func(ctx context.Context, username, secret string) (identity Identity, ok bool)

// GrantResolver downscopes requested scopes to the actions the identity may
// perform. Permission denial is represented by omitted actions, not an error.
type GrantResolver func(ctx context.Context, identity Identity, requested []Scope) ([]ResourceActions, error)

// Scope is a parsed registry token scope.
type Scope struct {
	Type    string
	Name    string
	Actions []string
}

// ResourceActions is the access claim shape defined by the Distribution token
// specification.
type ResourceActions struct {
	Type    string   `json:"type"`
	Class   string   `json:"class,omitempty"`
	Name    string   `json:"name"`
	Actions []string `json:"actions"`
}

// Claims is the complete JWT claim set issued by Go OMR. Standard claims use
// go-jose's types and validation; Access is the Docker Distribution extension.
type Claims struct {
	jwt.Claims
	Access []ResourceActions `json:"access"`
}

// TokenSigner signs algorithm-neutral registry claims.
type TokenSigner interface {
	Sign(*Claims) (string, error)
	KeyID() string
}

// TokenVerifier verifies a compact JWT and returns validated claims.
type TokenVerifier interface {
	Verify(string) (*Claims, error)
	KeyID() string
}
