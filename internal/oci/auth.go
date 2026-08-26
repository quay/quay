package oci

import "net/http"

// Authenticator validates credentials and authorizes registry access.
type Authenticator interface {
	Authenticate(r *http.Request, access ...Access) (*Grant, error)
}

// Access describes a requested operation on a registry resource.
type Access struct {
	Resource string // e.g. "repository:library/nginx"
	Action   string // "pull", "push", "delete"
}

// Grant is returned on successful authentication.
type Grant struct {
	User User
}

// User identifies an authenticated user.
type User struct {
	Name string
}

// AuthChallenge is returned by Authenticator when credentials are missing
// or invalid. Implementations set the appropriate response headers.
type AuthChallenge interface {
	error
	SetHeaders(w http.ResponseWriter)
}
