package oci

import (
	"context"
	"io"

	"github.com/opencontainers/go-digest"
)

// BlobStore defines content-addressable blob storage operations.
// Implementations must be safe for concurrent use.
type BlobStore interface {
	// Blob operations (content-addressed by digest)
	GetContent(ctx context.Context, dgst digest.Digest) ([]byte, error)
	PutContent(ctx context.Context, dgst digest.Digest, content []byte) error
	Reader(ctx context.Context, dgst digest.Digest, offset int64) (io.ReadCloser, error)
	Writer(ctx context.Context, dgst digest.Digest) (io.WriteCloser, error)
	Stat(ctx context.Context, dgst digest.Digest) (BlobInfo, error)
	Delete(ctx context.Context, dgst digest.Digest) error

	// Upload lifecycle
	InitUpload(ctx context.Context) (uploadID string, err error)
	UploadWriter(ctx context.Context, uploadID string, appendMode bool) (UploadWriter, error)
	UploadReader(ctx context.Context, uploadID string, offset int64) (io.ReadCloser, error)
	UploadStat(ctx context.Context, uploadID string) (BlobInfo, error)
	CommitUpload(ctx context.Context, uploadID string, dgst digest.Digest) error
	CancelUpload(ctx context.Context, uploadID string) error

	// Upload state (hashstates, startedat — keyed by uploadID + key)
	PutUploadState(ctx context.Context, uploadID string, key string, data []byte) error
	GetUploadState(ctx context.Context, uploadID string, key string) ([]byte, error)
	ListUploadState(ctx context.Context, uploadID string, keyPrefix string) ([]string, error)
}

// UploadWriter supports write, commit, cancel, and size tracking for uploads.
type UploadWriter interface {
	io.WriteCloser
	Size() int64
	Commit(ctx context.Context) error
	Cancel(ctx context.Context) error
}

// BlobInfo holds metadata about a stored blob.
type BlobInfo struct {
	Digest digest.Digest
	Size   int64
}
