package oci

import (
	"context"

	"github.com/opencontainers/go-digest"
)

// MetadataStore persists container registry metadata. Implementations must be
// safe for concurrent use from multiple goroutines.
type MetadataStore interface {
	// Write operations
	EnsureRepository(ctx context.Context, name RepositoryName) (int64, error)
	PutManifest(ctx context.Context, repoID int64, m ManifestRecord) (int64, error)
	DeleteManifest(ctx context.Context, repoID int64, dgst digest.Digest) error
	PutBlob(ctx context.Context, b BlobRecord) (int64, error)
	PutTag(ctx context.Context, repoID int64, t TagRecord) (int64, error)
	DeleteTag(ctx context.Context, repoID int64, tag string) error

	// Read operations
	GetRepositoryID(ctx context.Context, name RepositoryName) (int64, error)
	GetTagDigest(ctx context.Context, repoID int64, tag string) (digest.Digest, error)
	GetManifestDigest(ctx context.Context, repoID int64, dgst digest.Digest) (digest.Digest, error)
	GetManifestContent(ctx context.Context, dgst digest.Digest) ([]byte, error)
	BlobExists(ctx context.Context, dgst digest.Digest) (bool, error)
	BlobLinkedToRepo(ctx context.Context, repoID int64, dgst digest.Digest) (bool, error)
	ListTags(ctx context.Context, repoID int64) ([]string, error)
	ListRepositories(ctx context.Context) ([]RepositoryName, error)

	// Upload tracking (prevents GC of unreferenced blobs during push)
	PutUploadedBlob(ctx context.Context, repoID int64, dgst digest.Digest) error
	CleanExpiredUploadedBlobs(ctx context.Context) error
}

// ManifestRecord holds the data needed to persist a manifest.
type ManifestRecord struct {
	Digest       digest.Digest
	MediaType    string
	Content      []byte
	BlobDigests  []BlobRef
	ChildDigests []digest.Digest
	Tag          string
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
