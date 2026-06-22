package middleware

import (
	"context"
	"time"

	"github.com/distribution/distribution/v3"
	"github.com/distribution/distribution/v3/manifest/manifestlist"
	"github.com/opencontainers/go-digest"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"

	"github.com/quay/quay/internal/oci"
)

// manifestService wraps a distribution.ManifestService to record metadata on
// successful Put and Delete operations.
type manifestService struct {
	distribution.ManifestService
	repo *repository
}

func (ms *manifestService) Put(ctx context.Context, manifest distribution.Manifest, options ...distribution.ManifestServiceOption) (_ digest.Digest, retErr error) {
	defer recordOp("manifest_put", time.Now(), &retErr)

	dgst, err := ms.ManifestService.Put(ctx, manifest, options...)
	if err != nil {
		return dgst, err
	}

	repoID, err := ms.repo.ensureRepo(ctx)
	if err != nil {
		return "", err
	}

	mt, payload, err := manifest.Payload()
	if err != nil {
		return "", logMetadataError("manifest_put", ms.repo.Named().Name(), dgst.String(), err)
	}

	record := oci.ManifestRecord{
		Digest:    dgst,
		MediaType: mt,
		Content:   payload,
	}

	// Extract tag from options if present.
	for _, opt := range options {
		if withTag, ok := opt.(distribution.WithTagOption); ok {
			record.Tag = withTag.Tag
			break
		}
	}

	// Classify references as blobs or child manifests based on parent media type.
	if isIndexMediaType(mt) {
		for _, ref := range manifest.References() {
			record.ChildDigests = append(record.ChildDigests, ref.Digest)
		}
	} else {
		for _, ref := range manifest.References() {
			record.BlobDigests = append(record.BlobDigests, oci.BlobRef{
				Digest: ref.Digest,
				Size:   ref.Size,
			})
		}
	}

	if _, err := ms.repo.store.PutManifest(ctx, repoID, record); err != nil {
		return "", logMetadataError("manifest_put", ms.repo.Named().Name(), dgst.String(), err)
	}

	return dgst, nil
}

func (ms *manifestService) Delete(ctx context.Context, dgst digest.Digest) (retErr error) {
	defer recordOp("manifest_delete", time.Now(), &retErr)

	if err := ms.ManifestService.Delete(ctx, dgst); err != nil {
		return err
	}

	repoID, err := ms.repo.ensureRepo(ctx)
	if err != nil {
		return err
	}

	if err := ms.repo.store.DeleteManifest(ctx, repoID, dgst); err != nil {
		return logMetadataError("manifest_delete", ms.repo.Named().Name(), dgst.String(), err)
	}

	return nil
}

func isIndexMediaType(mt string) bool {
	return mt == manifestlist.MediaTypeManifestList ||
		mt == v1.MediaTypeImageIndex
}
