package oci

import (
	"errors"
	"fmt"

	"github.com/opencontainers/go-digest"
)

// Domain error sentinels.
var (
	ErrNotExist     = errors.New("not found")    //nolint:revive // sentinel
	ErrUnauthorized = errors.New("unauthorized") //nolint:revive // sentinel
)

// ErrBlobUnknown is returned when a blob with a specific digest is not known to the registry
type ErrBlobUnknown struct {
	Digest digest.Digest
}

// ErrChildManifestUnknown is returned when a child manifest of a manifest list or OCI index is
// unknown to the registry
type ErrChildManifestUnknown struct {
	Digest digest.Digest
}

func (e ErrBlobUnknown) Error() string {
	return fmt.Sprintf("blob unknown to registry: %s", e.Digest.String())
}

func (e ErrChildManifestUnknown) Error() string {
	return fmt.Sprintf("child manifest unknown to registry: %s", e.Digest.String())
}
