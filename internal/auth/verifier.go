package auth

import "context"

// Credentials are transport-neutral authentication credentials.
type Credentials struct {
	Username string
	Secret   string
}

// Verifier validates credentials and returns an authentication result.
type Verifier interface {
	Verify(context.Context, Credentials) Result
}
