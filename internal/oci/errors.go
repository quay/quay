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

// BlobUnknownError is returned when a blob with a specific digest is not known to the registry.
type BlobUnknownError struct {
	Digest digest.Digest
}

// ChildManifestUnknownError is returned when a child manifest of a manifest list or OCI index is
// unknown to the registry.
type ChildManifestUnknownError struct {
	Digest digest.Digest
}

func (e BlobUnknownError) Error() string {
	return fmt.Sprintf("blob unknown to registry: %s", e.Digest.String())
}

func (e ChildManifestUnknownError) Error() string {
	return fmt.Sprintf("child manifest unknown to registry: %s", e.Digest.String())
}
