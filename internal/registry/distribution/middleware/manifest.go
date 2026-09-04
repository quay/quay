package middleware

import (
	"context"
	"encoding/json"
	"errors"
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
	repo *repository
}

func (ms *manifestService) Put(ctx context.Context, manifest distribution.Manifest, options ...distribution.ManifestServiceOption) (_ digest.Digest, retErr error) {
	defer ms.repo.metrics.recordOp("manifest_put", time.Now(), &retErr)

	mt, payload, err := manifest.Payload()
	if err != nil {
		return "", logMetadataError("manifest_put", ms.repo.Named().Name(), "", err)
	}

	dgst := digest.FromBytes(payload)

	repoID, err := ms.repo.ensureRepo(ctx)
	if err != nil {
		return "", err
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

	record.Subject, record.ArtifactType = parseSubjectAndArtifactType(payload)
	if record.Subject != "" {
		SetSubject(ctx, record.Subject)
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
	defer ms.repo.metrics.recordOp("manifest_delete", time.Now(), &retErr)

	repoID, err := ms.repo.ensureRepo(ctx)
	if err != nil {
		return err
	}

	if err := ms.repo.store.DeleteManifest(ctx, repoID, dgst); err != nil {
		return logMetadataError("manifest_delete", ms.repo.Named().Name(), dgst.String(), err)
	}

	return nil
}

// parseSubjectAndArtifactType extracts the OCI subject digest and artifact
// type from a manifest's raw JSON payload. When artifactType is absent, it
// falls back to config.mediaType per the OCI spec.
func parseSubjectAndArtifactType(payload []byte) (subject digest.Digest, artifactType string) {
	var parsed struct {
		Subject *struct {
			Digest string `json:"digest"`
		} `json:"subject"`
		ArtifactType string `json:"artifactType"`
		Config       *struct {
			MediaType string `json:"mediaType"`
		} `json:"config"`
	}
	if json.Unmarshal(payload, &parsed) != nil {
		return "", ""
	}
	if parsed.Subject != nil && parsed.Subject.Digest != "" {
		if d, err := digest.Parse(parsed.Subject.Digest); err == nil {
			subject = d
		}
	}
	artifactType = parsed.ArtifactType
	if artifactType == "" && parsed.Config != nil {
		artifactType = parsed.Config.MediaType
	}
	return subject, artifactType
}

func isIndexMediaType(mt string) bool {
	return mt == manifestlist.MediaTypeManifestList ||
		mt == v1.MediaTypeImageIndex
}

// Exists checks if the manifest with the provided digest is stored in the database.
func (ms *manifestService) Exists(ctx context.Context, dgst digest.Digest) (_ bool, retErr error) {
	repoID, err := ms.repo.ensureRepo(ctx)
	if err != nil {
		return false, err
	}

	_, err = ms.repo.store.GetManifestDigest(ctx, repoID, dgst)

	if err == nil {
		return true, nil
	}

	if errors.Is(err, oci.ErrNotExist) {
		return false, nil
	}
	return false, err
}

// Get looks up the manifest on the provided digest and serves it directly to the client. Overrides normal Distribution lookup in the directory
// tree, the database is the single source of truth for image metadata. If lookup is successful, the manifest is delivered to the client.
// Otherwise, raises an error.
func (ms *manifestService) Get(ctx context.Context, dgst digest.Digest, options ...distribution.ManifestServiceOption) (_ distribution.Manifest, retErr error) {
	defer ms.repo.metrics.recordOp("manifest_get", time.Now(), &retErr)

	repoID, err := ms.repo.ensureRepo(ctx)
	if err != nil {
		return nil, err
	}

	// look up the manifest
	content, mediaType, err := ms.repo.store.GetManifestForServing(ctx, repoID, dgst)
	if err != nil {
		if errors.Is(err, oci.ErrNotExist) {
			return nil, distribution.ErrManifestUnknownRevision{
				Name:     ms.repo.Named().Name(),
				Revision: dgst,
			}
		}
		return nil, err
	}

	m, _, err := distribution.UnmarshalManifest(mediaType, content)
	if err != nil {
		return nil, err
	}

	return m, nil
}
