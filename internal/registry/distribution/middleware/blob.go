package middleware

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/distribution/distribution/v3"
	"github.com/opencontainers/go-digest"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"

	"github.com/quay/quay/internal/oci"
)

// blobStore wraps a distribution.BlobStore to record blob metadata on
// successful uploads. It intercepts Put (single-shot), Create (chunked
// upload start, including cross-repo mounts), and wraps the returned
// BlobWriter to intercept Commit.
type blobStore struct {
	distribution.BlobStore
	repo *repository
}

func (bs *blobStore) Put(ctx context.Context, mediaType string, p []byte) (_ v1.Descriptor, retErr error) {
	defer recordOp("blob_put", time.Now(), &retErr)

	expected := digest.FromBytes(p)
	unlock, err := bs.repo.locker.Lock(ctx, expected)
	if err != nil {
		return v1.Descriptor{}, err
	}
	defer unlock()

	desc, err := bs.BlobStore.Put(ctx, mediaType, p)
	if err != nil {
		return desc, err
	}
	if desc.Digest != expected {
		return v1.Descriptor{}, fmt.Errorf("middleware: blob put digest mismatch: got %s, expected %s", desc.Digest, expected)
	}

	if err := bs.recordBlob(ctx, desc); err != nil {
		return v1.Descriptor{}, err
	}
	return desc, nil
}

func (bs *blobStore) Create(ctx context.Context, options ...distribution.BlobCreateOption) (_ distribution.BlobWriter, retErr error) {
	defer recordOp("blob_create", time.Now(), &retErr)

	mountLock := &mountLockOption{ctx: ctx, locker: bs.repo.locker}
	coordinatedOptions := append([]distribution.BlobCreateOption(nil), options...)
	coordinatedOptions = append(coordinatedOptions, mountLock)

	wr, err := bs.BlobStore.Create(ctx, coordinatedOptions...)
	defer mountLock.release()
	if err != nil {
		// Distribution signals a successful cross-repo mount by returning
		// ErrBlobMounted with the descriptor.
		var mounted distribution.ErrBlobMounted
		if errors.As(err, &mounted) {
			if mountLock.unlock == nil {
				return nil, fmt.Errorf("middleware: mounted blob without digest coordination: %w", err)
			}
			if mounted.Descriptor.Digest != mountLock.dgst {
				return nil, fmt.Errorf("middleware: mounted blob digest mismatch: got %s, expected %s", mounted.Descriptor.Digest, mountLock.dgst)
			}
			if recErr := bs.recordBlob(ctx, mounted.Descriptor); recErr != nil {
				return nil, recErr
			}
			return nil, err
		}
		return nil, err
	}
	return &blobWriter{BlobWriter: wr, bs: bs}, nil
}

func (bs *blobStore) Resume(ctx context.Context, id string) (distribution.BlobWriter, error) {
	wr, err := bs.BlobStore.Resume(ctx, id)
	if err != nil {
		return nil, err
	}
	return &blobWriter{BlobWriter: wr, bs: bs}, nil
}

func (bs *blobStore) recordBlob(ctx context.Context, desc v1.Descriptor) error { //nolint:gocritic // distribution passes descriptors by value
	repoID, err := bs.repo.ensureRepo(ctx)
	if err != nil {
		return err
	}
	if _, err := bs.repo.store.PutRepositoryBlob(ctx, repoID, oci.BlobRecord{
		Digest: desc.Digest,
		Size:   desc.Size,
	}); err != nil {
		return logMetadataError("blob_put", bs.repo.Named().Name(), desc.Digest.String(), err)
	}
	return nil
}

// blobWriter wraps a distribution.BlobWriter to record metadata when the
// blob upload is committed.
type blobWriter struct {
	distribution.BlobWriter
	bs *blobStore
}

func (bw *blobWriter) Commit(ctx context.Context, provisional v1.Descriptor) (_ v1.Descriptor, retErr error) { //nolint:gocritic // interface compliance
	defer recordOp("blob_commit", time.Now(), &retErr)

	unlock, err := bw.bs.repo.locker.Lock(ctx, provisional.Digest)
	if err != nil {
		return v1.Descriptor{}, err
	}
	defer unlock()

	desc, err := bw.BlobWriter.Commit(ctx, provisional)
	if err != nil {
		return desc, err
	}
	if desc.Digest != provisional.Digest {
		return v1.Descriptor{}, fmt.Errorf("middleware: blob commit digest mismatch: got %s, expected %s", desc.Digest, provisional.Digest)
	}

	if err := bw.bs.recordBlob(ctx, desc); err != nil {
		return v1.Descriptor{}, err
	}
	return desc, nil
}

// Delete delegates to the inner store. No metadata cleanup is needed here---
// orphaned blob rows are handled by the garbage collector (FindOrphanedBlobs).
func (bs *blobStore) Delete(ctx context.Context, dgst digest.Digest) error {
	return bs.BlobStore.Delete(ctx, dgst)
}

type mountLockOption struct {
	ctx    context.Context
	locker oci.BlobLocker
	dgst   digest.Digest
	unlock func()
}

func (o *mountLockOption) Apply(value interface{}) error {
	options, ok := value.(*distribution.CreateOptions)
	if !ok {
		return fmt.Errorf("middleware: unexpected blob create options type %T", value)
	}
	if !options.Mount.ShouldMount {
		return nil
	}
	if o.unlock != nil {
		return fmt.Errorf("middleware: mount coordination option applied more than once")
	}

	o.dgst = options.Mount.From.Digest()
	unlock, err := o.locker.Lock(o.ctx, o.dgst)
	if err != nil {
		return err
	}
	o.unlock = unlock
	return nil
}

func (o *mountLockOption) release() {
	if o.unlock != nil {
		o.unlock()
	}
}
