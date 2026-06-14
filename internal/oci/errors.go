package oci

import "errors"

// Domain error sentinels.
var (
	ErrUnauthorized = errors.New("unauthorized") //nolint:revive // sentinel
)
