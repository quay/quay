// Package storage provides path helpers for content-addressable blob storage.
package storage

import (
	"errors"
)

// ErrNotExist is returned when a blob or upload does not exist.
var ErrNotExist = errors.New("blob does not exist")
