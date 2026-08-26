package oci

import "errors"

// Domain error sentinels.
var (
	ErrNotExist     = errors.New("not found")    //nolint:revive // sentinel
	ErrUnauthorized = errors.New("unauthorized") //nolint:revive // sentinel
)
