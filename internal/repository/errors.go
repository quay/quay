package repository

import "errors"

var (
	// ErrNotFound indicates the repository does not exist for this operation.
	ErrNotFound = errors.New("repository not found")
	// ErrForbidden indicates the actor cannot perform the operation.
	ErrForbidden = errors.New("forbidden")
	// ErrInvalidVisibility indicates the requested visibility is unsupported.
	ErrInvalidVisibility = errors.New("invalid visibility")
)
