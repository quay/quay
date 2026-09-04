package oci

import (
	"context"
	"time"

	"github.com/opencontainers/go-digest"
)

// PushTempTagExpiration is Python's PUSH_TEMP_TAG_EXPIRATION_SEC (3600).
// Digest-only manifest PUTs (skopeo multi-arch children) get a hidden $temp-
// tag for this long so Phase 2 GC cannot collect them before the index PUT.
const PushTempTagExpiration = time.Hour

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
	ListReferrers(ctx context.Context, repoID int64, subject digest.Digest, artifactType string) ([]ReferrerRecord, error)

	// Upload tracking (prevents GC of unreferenced blobs during push)
	PutRepositoryBlob(ctx context.Context, repoID int64, b BlobRecord) (int64, error)
	PutUploadedBlob(ctx context.Context, repoID int64, dgst digest.Digest) error
	DeleteUploadedBlob(ctx context.Context, repoID int64, dgst digest.Digest) (int64, error)
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
	Subject      digest.Digest
	ArtifactType string
	// TempTagExpiration, when >0 and Tag is empty, creates a hidden $temp-
	// tag that expires after this duration (Python create_manifest_with_temp_tag).
	TempTagExpiration time.Duration
}

// ReferrerRecord holds the metadata for a single referrer manifest.
type ReferrerRecord struct {
	Digest       string
	MediaType    string
	ArtifactType string
	Size         int64
	Annotations  map[string]string
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
