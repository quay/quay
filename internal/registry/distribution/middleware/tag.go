package middleware

import (
	"context"
	"time"

	"github.com/distribution/distribution/v3"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"

	"github.com/quay/quay/internal/dal/metastore"
)

// tagService wraps a distribution.TagService to record tag mutations in the
// metastore.
type tagService struct {
	distribution.TagService
	repo *repository
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

	if _, err := ts.repo.store.PutTag(ctx, repoID, metastore.TagRecord{
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
