package middleware

import (
	"context"
	"strings"
	"time"

	"github.com/distribution/distribution/v3"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"

	"github.com/quay/quay/internal/oci"
)

// tagService wraps a distribution.TagService to record tag mutations in the
// metastore.
type tagService struct {
	distribution.TagService
	repo *repository
}

func (ts *tagService) Get(ctx context.Context, tag string) (v1.Descriptor, error) {
	// Colons are invalid in OCI tags. When distribution receives a reference
	// like "sha256:totallywrong" it falls back to a tag lookup, but the
	// storage driver's PathRegexp rejects the colon and returns an untyped
	// InvalidPathError that the handler maps to 500. Short-circuit here with
	// a typed error the handler recognizes (→ MANIFEST_UNKNOWN, 404).
	if strings.Contains(tag, ":") {
		return v1.Descriptor{}, distribution.ErrTagUnknown{Tag: tag}
	}
	return ts.TagService.Get(ctx, tag)
}

func (ts *tagService) Tag(ctx context.Context, tag string, desc v1.Descriptor) (retErr error) { //nolint:gocritic // interface compliance
	defer recordOp("tag", time.Now(), &retErr)

	if err := ts.TagService.Tag(ctx, tag, desc); err != nil {
		return err
	}

	repoID, err := ts.repo.ensureRepo(ctx)
	if err != nil {
		return err
	}

	if _, err := ts.repo.store.PutTag(ctx, repoID, oci.TagRecord{
		Name:   tag,
		Digest: desc.Digest,
	}); err != nil {
		return logMetadataError("tag", ts.repo.Named().Name(), tag, err)
	}

	return nil
}

func (ts *tagService) Untag(ctx context.Context, tag string) (retErr error) {
	defer recordOp("untag", time.Now(), &retErr)

	if err := ts.TagService.Untag(ctx, tag); err != nil {
		return err
	}

	repoID, err := ts.repo.ensureRepo(ctx)
	if err != nil {
		return err
	}

	if err := ts.repo.store.DeleteTag(ctx, repoID, tag); err != nil {
		return logMetadataError("untag", ts.repo.Named().Name(), tag, err)
	}

	return nil
}
