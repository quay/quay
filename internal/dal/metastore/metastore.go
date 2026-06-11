// Package metastore defines the interface for persisting container registry
// metadata. The interface is database-agnostic; implementations live in the
// same package today (SQLite) and can be added for other backends (e.g.
// PostgreSQL) behind the same contract.
package metastore

import (
	"context"
	"strings"

	"github.com/distribution/reference"
	"github.com/opencontainers/go-digest"
)

// parseRepoName splits a distribution reference into namespace and repository.
// "library/nginx" → ("library", "nginx")
// "nginx" → ("library", "nginx")
// "org/team/repo" → ("org", "team/repo")
func parseRepoName(name reference.Named) (namespace, repo string) {
	full := reference.Path(name)
	if i := strings.IndexByte(full, '/'); i >= 0 {
		return full[:i], full[i+1:]
	}
	return "library", full
}

// Store persists container registry metadata. Implementations must be safe
// for concurrent use from multiple goroutines.
type Store interface {
	// EnsureRepository returns the ID of the named repository, creating it
	// and its namespace user if they do not exist.
	EnsureRepository(ctx context.Context, name reference.Named) (int64, error)

	// PutManifest records a manifest and atomically creates all associated
	// blob links, child-manifest links, and an optional tag. It returns the
	// database ID of the manifest row.
	PutManifest(ctx context.Context, repoID int64, m ManifestRecord) (int64, error)

	// DeleteManifest removes a manifest and its link rows by digest.
	DeleteManifest(ctx context.Context, repoID int64, dgst digest.Digest) error

	// PutBlob records blob metadata. Duplicate digests are a no-op.
	PutBlob(ctx context.Context, b BlobRecord) (int64, error)

	// PutTag creates or moves a tag to point at the given manifest digest.
	// Any existing active tag with the same name is expired first.
	PutTag(ctx context.Context, repoID int64, t TagRecord) (int64, error)

	// DeleteTag expires the active tag with the given name.
	DeleteTag(ctx context.Context, repoID int64, tag string) error
}

// ManifestRecord holds the data needed to persist a manifest.
type ManifestRecord struct {
	Digest       digest.Digest
	MediaType    string
	Content      []byte
	BlobDigests  []BlobRef
	ChildDigests []digest.Digest
	Tag          string // empty when pushed by digest only
}

// BlobRecord holds the data needed to persist blob metadata.
type BlobRecord struct {
	Digest digest.Digest
	Size   int64
}

// BlobRef identifies a blob referenced by a manifest.
type BlobRef struct {
	Digest digest.Digest
	Size   int64
}

// TagRecord associates a tag name with a manifest digest.
type TagRecord struct {
	Name   string
	Digest digest.Digest
}
