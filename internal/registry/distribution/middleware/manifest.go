package middleware

import (
	"context"
	"encoding/json"
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
	defer ms.repo.metrics.recordOp("manifest_put", time.Now(), &retErr)

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

	// Digest-only PUTs (no WithTag) match Python write_manifest_by_digest:
	// a hidden $temp- tag keeps the manifest alive for 1 hour so multi-arch
	// children are not collected before the index PUT links them.
	if record.Tag == "" {
		record.TempTagExpiration = oci.PushTempTagExpiration
	}

	record.Subject, record.ArtifactType = parseSubjectAndArtifactType(payload)
	if record.Subject != "" {
		SetSubject(ctx, record.Subject)
	}

	// Classify references as blobs or child manifests based on parent media type.
	if isIndexMediaType(mt) {
		blobs := ms.repo.Repository.Blobs(ctx)
		for _, ref := range manifest.References() {
			record.ChildDigests = append(record.ChildDigests, ref.Digest)
			if child, ok := loadChildFromCAS(ctx, blobs, ref); ok {
				record.ChildManifests = append(record.ChildManifests, child)
			}
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

// loadChildFromCAS reads a child manifest from the blob store and classifies
// its config/layers (or nested children). A miss is not fatal: Python only
// fails the whole create on a hard load error, and distribution already
// accepted the index. The metastore then either finds an existing row or
// inserts a non-clobbering stub.
func loadChildFromCAS(ctx context.Context, blobs distribution.BlobStore, ref v1.Descriptor) (oci.ManifestRecord, bool) { //nolint:gocritic // descriptor comes from distribution by value
	if blobs == nil || ref.Digest == "" {
		return oci.ManifestRecord{}, false
	}
	content, err := blobs.Get(ctx, ref.Digest)
	if err != nil || len(content) == 0 {
		return oci.ManifestRecord{}, false
	}
	rec := parseChildRecord(ref, content)
	if len(rec.ChildDigests) == 0 {
		return rec, true
	}
	var nested struct {
		Manifests []v1.Descriptor `json:"manifests"`
	}
	_ = json.Unmarshal(content, &nested)
	for _, childRef := range nested.Manifests {
		if child, ok := loadChildFromCAS(ctx, blobs, childRef); ok {
			rec.ChildManifests = append(rec.ChildManifests, child)
		}
	}
	return rec, true
}

func parseChildRecord(ref v1.Descriptor, content []byte) oci.ManifestRecord { //nolint:gocritic // descriptor comes from distribution by value
	var parsed struct {
		MediaType string          `json:"mediaType"`
		Config    *v1.Descriptor  `json:"config"`
		Layers    []v1.Descriptor `json:"layers"`
		Manifests []v1.Descriptor `json:"manifests"`
	}
	_ = json.Unmarshal(content, &parsed)

	mt := ref.MediaType
	if mt == "" {
		mt = parsed.MediaType
	}
	rec := oci.ManifestRecord{
		Digest:    ref.Digest,
		MediaType: mt,
		Content:   content,
	}
	rec.Subject, rec.ArtifactType = parseSubjectAndArtifactType(content)

	if isIndexMediaType(mt) || len(parsed.Manifests) > 0 {
		for _, m := range parsed.Manifests {
			rec.ChildDigests = append(rec.ChildDigests, m.Digest)
		}
		return rec
	}
	if parsed.Config != nil && parsed.Config.Digest != "" {
		rec.BlobDigests = append(rec.BlobDigests, oci.BlobRef{
			Digest: parsed.Config.Digest,
			Size:   parsed.Config.Size,
		})
	}
	for _, layer := range parsed.Layers {
		if layer.Digest == "" {
			continue
		}
		rec.BlobDigests = append(rec.BlobDigests, oci.BlobRef{
			Digest: layer.Digest,
			Size:   layer.Size,
		})
	}
	return rec
}
