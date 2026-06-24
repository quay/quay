// Package middleware provides a distribution/v3 repository middleware that
// records registry metadata in a metastore.Store. It intercepts manifest
// pushes, blob uploads, and tag operations, writing metadata to the database
// after the underlying storage operation succeeds.
//
// Registration is explicit—call Register from main, not from an init function.
package middleware

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"sync"

	"github.com/distribution/distribution/v3"
	"github.com/distribution/reference"

	repositorymiddleware "github.com/distribution/distribution/v3/registry/middleware/repository"

	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
)

const middlewareName = "quaydb"

// Register registers the metadata-recording middleware with distribution's
// repository middleware registry. It must be called before
// handlers.NewApp so that the middleware config reference resolves.
//
// The store is captured by closure—no options map is needed at runtime.
func Register(store metastore.Store, libraryNamespace string) error {
	return repositorymiddleware.Register(middlewareName, func(
		ctx context.Context,
		repo distribution.Repository,
		_ map[string]interface{},
	) (distribution.Repository, error) {
		return newRepository(repo, store, libraryNamespace), nil
	})
}

// Name returns the name used to register with distribution. Use this in
// configuration to avoid string duplication.
func Name() string { return middlewareName }

// repository wraps a distribution.Repository to intercept metadata-producing
// operations. It resolves the repository ID lazily on the first write and
// caches it for the lifetime of the request (the middleware wrapper is
// per-request, so this is safe).
type repository struct {
	distribution.Repository
	store            metastore.Store
	libraryNamespace string

	repoOnce sync.Once
	repoID   int64
	repoErr  error
}

func newRepository(inner distribution.Repository, store metastore.Store, libraryNamespace string) *repository {
	return &repository{Repository: inner, store: store, libraryNamespace: libraryNamespace}
}

func (r *repository) Named() reference.Named { return r.Repository.Named() }

func (r *repository) Manifests(ctx context.Context, options ...distribution.ManifestServiceOption) (distribution.ManifestService, error) {
	inner, err := r.Repository.Manifests(ctx, options...)
	if err != nil {
		return nil, err
	}
	return &manifestService{
		ManifestService: inner,
		repo:            r,
	}, nil
}

func (r *repository) Blobs(ctx context.Context) distribution.BlobStore {
	return &blobStore{
		BlobStore: r.Repository.Blobs(ctx),
		repo:      r,
	}
}

func (r *repository) Tags(ctx context.Context) distribution.TagService {
	return &tagService{
		TagService: r.Repository.Tags(ctx),
		repo:       r,
	}
}

// repoName converts this repository's distribution reference to an oci.RepositoryName.
func (r *repository) repoName() oci.RepositoryName {
	full := reference.Path(r.Named())
	if i := strings.IndexByte(full, '/'); i >= 0 {
		return oci.RepositoryName{Namespace: full[:i], Name: full[i+1:]}
	}
	return oci.RepositoryName{Namespace: r.libraryNamespace, Name: full}
}

// ensureRepo resolves (or creates) the repository in the metastore, returning
// its database ID. The result is cached for the lifetime of this repository
// wrapper (one per request) to avoid redundant transactions on multi-layer pushes.
func (r *repository) ensureRepo(ctx context.Context) (int64, error) {
	r.repoOnce.Do(func() {
		name := r.repoName()
		r.repoID, r.repoErr = r.store.EnsureRepository(ctx, name)
		if r.repoErr != nil {
			r.repoErr = fmt.Errorf("middleware: ensure repository %s: %w", r.Named().Name(), r.repoErr)
		}
	})
	return r.repoID, r.repoErr
}

// MetadataWriteError is logged when a storage operation succeeds but the
// corresponding metadata write fails. The registry operation is still failed
// to the client to prevent silent inconsistency.
type MetadataWriteError struct {
	Operation string
	RepoName  string
	Detail    string
	Err       error
}

func (e *MetadataWriteError) Error() string {
	return fmt.Sprintf("metadata write failed: %s %s %s: %v", e.Operation, e.RepoName, e.Detail, e.Err)
}

func (e *MetadataWriteError) Unwrap() error { return e.Err }

func logMetadataError(op, repo, detail string, err error) error {
	mwe := &MetadataWriteError{Operation: op, RepoName: repo, Detail: detail, Err: err}
	slog.Error("metadata write failed",
		"operation", op, "repository", repo, "detail", detail, "err", err)
	return mwe
}
