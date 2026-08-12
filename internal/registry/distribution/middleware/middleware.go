// Package middleware provides a distribution/v3 repository middleware that
// records registry metadata in a metastore.Store. It intercepts manifest
// pushes, blob uploads, and tag operations, writing metadata to the database
// after the underlying storage operation succeeds.
//
// Registration is explicit---call Register from main, not from an init function.
package middleware

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"sync"

	"github.com/distribution/distribution/v3"
	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/reference"

	repositorymiddleware "github.com/distribution/distribution/v3/registry/middleware/repository"

	"github.com/quay/quay/internal/oci"
)

const (
	middlewareName            = "quaydb"
	storeParameter            = "metastore"
	blobLockerParameter       = "bloblocker"
	libraryNamespaceParameter = "librarynamespace"
	metricsParameter          = "metrics"
)

var registerOnce sync.Once
var errRegister error

// Register makes the stateless metadata-recording middleware factory available
// to distribution. It must be called before handlers.NewApp so that the
// middleware config reference resolves. It is safe to call multiple times and
// concurrently.
func Register() error {
	registerOnce.Do(func() {
		errRegister = repositorymiddleware.Register(middlewareName, newRepositoryMiddleware)
	})
	return errRegister
}

// Name returns the name used to register with distribution. Use this in
// configuration to avoid string duplication.
func Name() string { return middlewareName }

// Option configures optional middleware parameters.
type Option func(configuration.Parameters)

// WithMetrics attaches per-instance Prometheus metrics to the middleware
// parameters. When m is nil the option is a no-op and metric recording is
// disabled.
func WithMetrics(m *Metrics) Option {
	return func(p configuration.Parameters) {
		if m != nil {
			p[metricsParameter] = m
		}
	}
}

// Parameters builds distribution parameters for the metadata-recording
// middleware. The values are kept in the per-registry configuration rather than
// in the globally registered factory. Optional settings (e.g. metrics) are
// provided via Option values; omitting them is safe and preserves backward
// compatibility.
func Parameters(store oci.MetadataStore, locker oci.BlobLocker, libraryNamespace string, opts ...Option) configuration.Parameters {
	p := configuration.Parameters{
		storeParameter:            store,
		blobLockerParameter:       locker,
		libraryNamespaceParameter: libraryNamespace,
	}
	for _, o := range opts {
		o(p)
	}
	return p
}

func newRepositoryMiddleware(_ context.Context, repo distribution.Repository, options map[string]interface{}) (distribution.Repository, error) {
	store, ok := options[storeParameter].(oci.MetadataStore)
	if !ok || store == nil {
		return nil, fmt.Errorf("middleware: %s parameter must implement oci.MetadataStore", storeParameter)
	}
	locker, ok := options[blobLockerParameter].(oci.BlobLocker)
	if !ok || locker == nil {
		return nil, fmt.Errorf("middleware: %s parameter must implement oci.BlobLocker", blobLockerParameter)
	}
	libraryNamespace, ok := options[libraryNamespaceParameter].(string)
	if !ok || libraryNamespace == "" {
		return nil, fmt.Errorf("middleware: %s parameter must be a non-empty string", libraryNamespaceParameter)
	}
	// Metrics are optional; nil disables metric recording.
	metrics, _ := options[metricsParameter].(*Metrics)
	return newRepository(repo, store, locker, libraryNamespace, metrics), nil
}

// repository wraps a distribution.Repository to intercept metadata-producing
// operations. It resolves the repository ID lazily on the first write and
// caches it for the lifetime of the request (the middleware wrapper is
// per-request, so this is safe).
type repository struct {
	distribution.Repository
	store            oci.MetadataStore
	locker           oci.BlobLocker
	libraryNamespace string
	metrics          *Metrics

	repoOnce sync.Once
	repoID   int64
	repoErr  error
}

func newRepository(inner distribution.Repository, store oci.MetadataStore, locker oci.BlobLocker, libraryNamespace string, metrics *Metrics) *repository {
	return &repository{Repository: inner, store: store, locker: locker, libraryNamespace: libraryNamespace, metrics: metrics}
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
// Named().Name() returns the repo path without a hostname when distribution
// creates the reference internally (e.g. "projectquay/clair"). reference.Path()
// would incorrectly strip the first segment as a hostname.
func (r *repository) repoName() oci.RepositoryName {
	full := r.Named().Name()
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
