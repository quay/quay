package oci

import (
	"errors"

	"github.com/opencontainers/go-digest"
)

// Domain error sentinels.
var (
	ErrNotExist     = errors.New("not found")    //nolint:revive // sentinel
	ErrUnauthorized = errors.New("unauthorized") //nolint:revive // sentinel
)

// ChildManifestUnknownError reports an image index that references a child
// manifest which is not in the catalog. It matches ErrNotExist with errors.Is
// so existing not-found handling still applies, and carries the child digest
// so the registry can answer MANIFEST_BLOB_UNKNOWN for that digest.
type ChildManifestUnknownError struct {
	Digest digest.Digest
}

func (e ChildManifestUnknownError) Error() string {
	return "child manifest " + e.Digest.String() + ": " + ErrNotExist.Error()
}

// Is reports whether target is ErrNotExist.
func (e ChildManifestUnknownError) Is(target error) bool {
	return errors.Is(target, ErrNotExist)
}
