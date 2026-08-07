package mirrorregistry_test

import (
	"encoding/json"
	"net/http"
	"net/url"
	"strings"
	"testing"

	"github.com/opencontainers/go-digest"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/e2e/mirrorregistry/internal/e2etest"
)

const (
	imageManifestMediaType = "application/vnd.oci.image.manifest.v1+json"
	imageConfigMediaType   = "application/vnd.oci.image.config.v1+json"
	imageLayerMediaType    = "application/vnd.oci.image.layer.v1.tar+gzip"
	imageIndexMediaType    = "application/vnd.oci.image.index.v1+json"
	emptyConfigMediaType   = "application/vnd.oci.empty.v1+json"
	artifactType           = "application/vnd.example.sbom.v1"
	signatureArtifactType  = "application/vnd.example.signature.v1"
)

type descriptor struct {
	MediaType string        `json:"mediaType"`
	Digest    digest.Digest `json:"digest"`
	Size      int64         `json:"size"`
}

type imageManifest struct {
	SchemaVersion int          `json:"schemaVersion"`
	MediaType     string       `json:"mediaType"`
	Config        descriptor   `json:"config"`
	Layers        []descriptor `json:"layers"`
}

type artifactManifest struct {
	SchemaVersion int          `json:"schemaVersion"`
	MediaType     string       `json:"mediaType"`
	ArtifactType  string       `json:"artifactType"`
	Config        descriptor   `json:"config"`
	Layers        []descriptor `json:"layers"`
	Subject       descriptor   `json:"subject"`
}

type imageIndex struct {
	SchemaVersion int                  `json:"schemaVersion"`
	MediaType     string               `json:"mediaType"`
	Manifests     []platformDescriptor `json:"manifests"`
}

type platformDescriptor struct {
	MediaType string        `json:"mediaType"`
	Digest    digest.Digest `json:"digest"`
	Size      int64         `json:"size"`
	Platform  platform      `json:"platform"`
}

type platform struct {
	Architecture string `json:"architecture"`
	OS           string `json:"os"`
}

func TestRegistryPushPullLifecycle(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-image"

	parsedURL, err := url.Parse(h.BaseURL())
	require.NoError(t, err)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, h.BaseURL()+"/v2/"+repository+"/manifests/latest", http.NoBody)
	require.NoError(t, err)
	resp, err := h.HTTPClient().Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusUnauthorized, resp.StatusCode)
	challenge := resp.Header.Get("WWW-Authenticate")
	assert.Contains(t, challenge, `Bearer realm="`+h.BaseURL()+`/v2/auth"`)
	assert.Contains(t, challenge, `service="`+parsedURL.Host+`"`)
	assert.Contains(t, challenge, `scope="repository:`+repository+`:pull"`)

	client := h.Registry()

	configBytes := []byte(`{"architecture":"amd64","os":"linux"}`)
	layerBytes := []byte("deterministic layer contents")
	configDigest, err := client.PushBlob(ctx, repository, configBytes)
	require.NoError(t, err)
	layerDigest, err := client.PushBlob(ctx, repository, layerBytes)
	require.NoError(t, err)

	manifestBytes, err := json.Marshal(imageManifest{
		SchemaVersion: 2,
		MediaType:     imageManifestMediaType,
		Config: descriptor{
			MediaType: imageConfigMediaType,
			Digest:    configDigest,
			Size:      int64(len(configBytes)),
		},
		Layers: []descriptor{{
			MediaType: imageLayerMediaType,
			Digest:    layerDigest,
			Size:      int64(len(layerBytes)),
		}},
	})
	require.NoError(t, err)

	manifestResponse, err := client.PutManifest(ctx, repository, "latest", manifestBytes, imageManifestMediaType)
	require.NoError(t, err)
	assert.Equal(t, digest.FromBytes(manifestBytes), manifestResponse.Digest)
	manifestDigest := manifestResponse.Digest

	head, err := client.HeadManifest(ctx, repository, "latest")
	require.NoError(t, err)
	assert.Equal(t, manifestDigest, head.Digest)
	assert.Contains(t, head.MediaType, imageManifestMediaType)
	assert.Empty(t, head.Body)

	byTag, err := client.GetManifest(ctx, repository, "latest")
	require.NoError(t, err)
	assert.Equal(t, manifestBytes, byTag.Body)
	assert.Equal(t, manifestDigest, byTag.Digest)
	assert.Contains(t, byTag.MediaType, imageManifestMediaType)

	byDigest, err := client.GetManifest(ctx, repository, manifestDigest.String())
	require.NoError(t, err)
	assert.Equal(t, manifestBytes, byDigest.Body)

	gotConfig, err := client.GetBlob(ctx, repository, configDigest)
	require.NoError(t, err)
	assert.Equal(t, configBytes, gotConfig)
	gotLayer, err := client.GetBlob(ctx, repository, layerDigest)
	require.NoError(t, err)
	assert.Equal(t, layerBytes, gotLayer)

	tags, err := client.ListTags(ctx, repository)
	require.NoError(t, err)
	assert.Contains(t, tags, "latest")

	require.NoError(t, client.DeleteManifest(ctx, repository, manifestDigest))
	_, err = client.GetManifest(ctx, repository, "latest")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 404")
}

func TestRegistryTokenScopeEnforcement(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-token-scope"

	pullOnlyToken, err := h.Registry().RequestToken(ctx, repository, "pull")
	require.NoError(t, err)
	_, err = h.Registry().PushBlobWithToken(ctx, repository, []byte("forbidden upload"), pullOnlyToken)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 401")

	pushToken, err := h.Registry().RequestToken(ctx, repository, "pull", "push")
	require.NoError(t, err)
	configBytes := []byte(`{"architecture":"amd64","os":"linux"}`)
	configDigest, err := h.Registry().PushBlobWithToken(ctx, repository, configBytes, pushToken)
	require.NoError(t, err)
	layerBytes := []byte("scope-authorized layer")
	layerDigest, err := h.Registry().PushBlobWithToken(ctx, repository, layerBytes, pushToken)
	require.NoError(t, err)
	manifestBytes, err := json.Marshal(imageManifest{
		SchemaVersion: 2,
		MediaType:     imageManifestMediaType,
		Config:        descriptor{MediaType: imageConfigMediaType, Digest: configDigest, Size: int64(len(configBytes))},
		Layers:        []descriptor{{MediaType: imageLayerMediaType, Digest: layerDigest, Size: int64(len(layerBytes))}},
	})
	require.NoError(t, err)
	response, err := h.Registry().PutManifestWithToken(ctx, repository, "latest", manifestBytes, imageManifestMediaType, pushToken)
	require.NoError(t, err)
	assert.Equal(t, digest.FromBytes(manifestBytes), response.Digest)

	pulled, err := h.Registry().GetManifest(ctx, repository, "latest")
	require.NoError(t, err)
	assert.Equal(t, manifestBytes, pulled.Body)
}

func TestRegistryDeleteGarbageCollectAndRepush(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-gc"

	configBytes := []byte(`{"architecture":"amd64","os":"linux"}`)
	layerBytes := []byte("garbage-collected layer")
	image := pushImage(t, h, repository, "latest", configBytes, layerBytes)

	require.NoError(t, h.Registry().DeleteManifest(ctx, repository, image.digest))
	assertRegistryMissing(t, h, repository, "latest")
	gotLayer, err := h.Registry().GetBlob(ctx, repository, image.layer)
	require.NoError(t, err)
	assert.Equal(t, layerBytes, gotLayer)

	protectedStats, err := h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Zero(t, protectedStats.BlobsDeleted)
	gotLayer, err = h.Registry().GetBlob(ctx, repository, image.layer)
	require.NoError(t, err)
	assert.Equal(t, layerBytes, gotLayer)

	require.NoError(t, h.ExpireUploadProtection(ctx))
	stats, err := h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Zero(t, stats.TagsExpired)
	assert.Zero(t, stats.ManifestsDeleted)
	assert.Equal(t, 2, stats.BlobsDeleted)
	assert.Equal(t, int64(len(configBytes)+len(layerBytes)), stats.BytesReclaimed)
	assertBlobMissing(t, h, repository, image.config)
	assertBlobMissing(t, h, repository, image.layer)

	repushed := pushImage(t, h, repository, "latest", configBytes, layerBytes)
	assert.Equal(t, image.digest, repushed.digest)
	manifest, err := h.Registry().GetManifest(ctx, repository, "latest")
	require.NoError(t, err)
	assert.Equal(t, repushed.manifest, manifest.Body)
}

func TestRegistryMultiArchGarbageCollectionCascade(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-multiarch"

	amd64Config := []byte(`{"architecture":"amd64","os":"linux"}`)
	amd64Layer := []byte("linux-amd64 layer")
	amd64 := pushImage(t, h, repository, "", amd64Config, amd64Layer)
	arm64Config := []byte(`{"architecture":"arm64","os":"linux"}`)
	arm64Layer := []byte("linux-arm64 layer")
	arm64 := pushImage(t, h, repository, "", arm64Config, arm64Layer)

	indexBytes, err := json.Marshal(imageIndex{
		SchemaVersion: 2,
		MediaType:     imageIndexMediaType,
		Manifests: []platformDescriptor{
			{
				MediaType: imageManifestMediaType,
				Digest:    amd64.digest,
				Size:      int64(len(amd64.manifest)),
				Platform:  platform{Architecture: "amd64", OS: "linux"},
			},
			{
				MediaType: imageManifestMediaType,
				Digest:    arm64.digest,
				Size:      int64(len(arm64.manifest)),
				Platform:  platform{Architecture: "arm64", OS: "linux"},
			},
		},
	})
	require.NoError(t, err)
	indexResponse, err := h.Registry().PutManifest(ctx, repository, "latest", indexBytes, imageIndexMediaType)
	require.NoError(t, err)
	assert.Equal(t, digest.FromBytes(indexBytes), indexResponse.Digest)

	byTag, err := h.Registry().GetManifest(ctx, repository, "latest")
	require.NoError(t, err)
	assert.Equal(t, indexBytes, byTag.Body)
	assert.Contains(t, byTag.MediaType, imageIndexMediaType)
	byDigest, err := h.Registry().GetManifest(ctx, repository, indexResponse.Digest.String())
	require.NoError(t, err)
	assert.Equal(t, indexBytes, byDigest.Body)
	for _, child := range []pushedImage{amd64, arm64} {
		manifest, err := h.Registry().GetManifest(ctx, repository, child.digest.String())
		require.NoError(t, err)
		assert.Equal(t, child.manifest, manifest.Body)
		_, err = h.Registry().GetBlob(ctx, repository, child.config)
		require.NoError(t, err)
		_, err = h.Registry().GetBlob(ctx, repository, child.layer)
		require.NoError(t, err)
	}

	require.NoError(t, h.Registry().DeleteManifest(ctx, repository, indexResponse.Digest))
	stats, err := h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, stats.ManifestsDeleted)
	assert.Zero(t, stats.BlobsDeleted)

	require.NoError(t, h.ExpireUploadProtection(ctx))
	stats, err = h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Zero(t, stats.ManifestsDeleted)
	assert.Equal(t, 4, stats.BlobsDeleted)
	assert.Equal(t, int64(len(amd64Config)+len(amd64Layer)+len(arm64Config)+len(arm64Layer)), stats.BytesReclaimed)
	assertRegistryMissing(t, h, repository, "latest")
	// GC removes both child metadata rows, but Distribution digest revision
	// links remain readable until manifest-link collection is implemented.
	// Blob 404s below prove the collected child images are no longer usable.
	for _, child := range []pushedImage{amd64, arm64} {
		assertBlobMissing(t, h, repository, child.config)
		assertBlobMissing(t, h, repository, child.layer)
	}
}

func TestRegistryCrossRepositoryMountSurvivesGarbageCollection(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const (
		sourceRepository = "admin/e2e-mount-source"
		targetRepository = "admin/e2e-mount-target"
	)

	sourceConfig := []byte(`{"image":"source"}`)
	sharedLayer := []byte("cross-repository shared layer")
	source := pushImage(t, h, sourceRepository, "latest", sourceConfig, sharedLayer)

	require.NoError(t, h.Registry().MountBlob(ctx, sourceRepository, targetRepository, source.layer))
	targetConfig := []byte(`{"image":"target"}`)
	targetConfigDigest, err := h.Registry().PushBlob(ctx, targetRepository, targetConfig)
	require.NoError(t, err)
	target := putImageManifest(
		t,
		h,
		targetRepository,
		"latest",
		targetConfig,
		targetConfigDigest,
		sharedLayer,
		source.layer,
	)
	require.NoError(t, h.ExpireUploadProtection(ctx))

	require.NoError(t, h.Registry().DeleteManifest(ctx, sourceRepository, source.digest))
	stats, err := h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Equal(t, 1, stats.BlobsDeleted)
	assert.Equal(t, int64(len(sourceConfig)), stats.BytesReclaimed)
	assertBlobMissing(t, h, sourceRepository, source.layer)
	gotSharedLayer, err := h.Registry().GetBlob(ctx, targetRepository, source.layer)
	require.NoError(t, err)
	assert.Equal(t, sharedLayer, gotSharedLayer)

	require.NoError(t, h.Registry().DeleteManifest(ctx, targetRepository, target.digest))
	stats, err = h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, stats.BlobsDeleted)
	assert.Equal(t, int64(len(targetConfig)+len(sharedLayer)), stats.BytesReclaimed)
	assertBlobMissing(t, h, targetRepository, source.layer)
}

func TestRegistryReferrersLifecycle(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-referrers"

	configBytes := []byte(`{}`)
	layerBytes := []byte("subject layer")
	subject := pushImage(t, h, repository, "subject", configBytes, layerBytes)
	sbom := pushArtifact(t, h, repository, subject, configBytes, artifactType, []byte("SBOM payload"))
	signature := pushArtifact(t, h, repository, subject, configBytes, signatureArtifactType, []byte("signature payload"))

	tags, err := h.Registry().ListTags(ctx, repository)
	require.NoError(t, err)
	assert.Contains(t, tags, "subject")
	for _, tag := range tags {
		assert.False(t, strings.HasPrefix(tag, "$temp-"), "hidden referrer protection tag leaked through tag listing")
	}

	referrers, err := h.Registry().GetReferrers(ctx, repository, subject.digest)
	require.NoError(t, err)
	require.Equal(t, 2, referrers.SchemaVersion)
	require.Equal(t, imageIndexMediaType, referrers.MediaType)
	require.Len(t, referrers.Manifests, 2)
	assert.ElementsMatch(t, []string{sbom.digest.String(), signature.digest.String()}, []string{
		referrers.Manifests[0].Digest,
		referrers.Manifests[1].Digest,
	})

	filtered, err := h.Registry().GetReferrersByArtifactType(ctx, repository, subject.digest, artifactType)
	require.NoError(t, err)
	assert.Equal(t, "artifactType", filtered.FiltersApplied)
	require.Len(t, filtered.Manifests, 1)
	assert.Equal(t, sbom.digest.String(), filtered.Manifests[0].Digest)
	assert.Equal(t, imageManifestMediaType, filtered.Manifests[0].MediaType)
	assert.Equal(t, int64(len(sbom.manifest)), filtered.Manifests[0].Size)
	assert.Equal(t, artifactType, filtered.Manifests[0].ArtifactType)

	filtered, err = h.Registry().GetReferrersByArtifactType(ctx, repository, subject.digest, "application/vnd.example.missing")
	require.NoError(t, err)
	assert.Equal(t, "artifactType", filtered.FiltersApplied)
	assert.Empty(t, filtered.Manifests)

	require.NoError(t, h.ExpireUploadProtection(ctx))
	require.NoError(t, h.Registry().DeleteManifest(ctx, repository, subject.digest))
	// Current policy gives digest-pushed referrers non-expiring hidden tags,
	// so deleting only the subject must not collect the referrers.
	stats, err := h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Zero(t, stats.ManifestsDeleted)
	assert.Equal(t, 1, stats.BlobsDeleted)
	assert.Equal(t, int64(len(layerBytes)), stats.BytesReclaimed)
	assertRegistryMissing(t, h, repository, "subject")
	_, err = h.Registry().GetManifest(ctx, repository, sbom.digest.String())
	require.NoError(t, err)
	_, err = h.Registry().GetManifest(ctx, repository, signature.digest.String())
	require.NoError(t, err)

	require.NoError(t, h.Registry().DeleteManifest(ctx, repository, sbom.digest))
	require.NoError(t, h.Registry().DeleteManifest(ctx, repository, signature.digest))
	stats, err = h.CollectGarbage(ctx)
	require.NoError(t, err)
	assert.Equal(t, 3, stats.BlobsDeleted)
	assert.Equal(t, int64(len(configBytes)+len(sbom.payload)+len(signature.payload)), stats.BytesReclaimed)
	assertBlobMissing(t, h, repository, sbom.blob)
	assertBlobMissing(t, h, repository, signature.blob)
	referrers, err = h.Registry().GetReferrers(ctx, repository, subject.digest)
	require.NoError(t, err)
	assert.Empty(t, referrers.Manifests)
}

func TestHarnessRestartPreservesRegistryState(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-restart"
	configBytes := []byte(`{"architecture":"amd64","os":"linux"}`)
	layerBytes := []byte("persistent layer")
	image := pushImage(t, h, repository, "latest", configBytes, layerBytes)

	h = h.Restart(t)
	manifest, err := h.Registry().GetManifest(t.Context(), repository, "latest")
	require.NoError(t, err)
	assert.Equal(t, image.manifest, manifest.Body)
	assert.Equal(t, image.digest, manifest.Digest)
	config, err := h.Registry().GetBlob(t.Context(), repository, image.config)
	require.NoError(t, err)
	assert.Equal(t, configBytes, config)
	layer, err := h.Registry().GetBlob(t.Context(), repository, image.layer)
	require.NoError(t, err)
	assert.Equal(t, layerBytes, layer)
	tags, err := h.Registry().ListTags(t.Context(), repository)
	require.NoError(t, err)
	assert.Contains(t, tags, "latest")
}

func TestHarnessInstancesAreIsolated(t *testing.T) {
	first := e2etest.New(t)
	second := e2etest.New(t)

	firstImage := pushUniqueImage(t, first, "first-content")
	secondImage := pushUniqueImage(t, second, "second-content")

	firstManifest, err := first.Registry().GetManifest(t.Context(), "admin/shared-name", "latest")
	require.NoError(t, err)
	assert.Equal(t, firstImage.manifest, firstManifest.Body)
	assert.NotEqual(t, secondImage.manifest, firstManifest.Body)

	secondManifest, err := second.Registry().GetManifest(t.Context(), "admin/shared-name", "latest")
	require.NoError(t, err)
	assert.Equal(t, secondImage.manifest, secondManifest.Body)
	assert.NotEqual(t, firstImage.manifest, secondManifest.Body)

	_, err = first.Registry().GetBlob(t.Context(), "admin/shared-name", secondImage.layer)
	require.Error(t, err)
	_, err = second.Registry().GetBlob(t.Context(), "admin/shared-name", firstImage.layer)
	require.Error(t, err)
}

type pushedImage struct {
	manifest []byte
	digest   digest.Digest
	config   digest.Digest
	layer    digest.Digest
}

type pushedArtifact struct {
	manifest []byte
	payload  []byte
	digest   digest.Digest
	blob     digest.Digest
}

func pushUniqueImage(t *testing.T, h *e2etest.Harness, content string) pushedImage {
	t.Helper()
	return pushImage(t, h, "admin/shared-name", "latest", []byte(`{}`), []byte(content))
}

func pushImage(t *testing.T, h *e2etest.Harness, repository, reference string, configBytes, layerBytes []byte) pushedImage {
	t.Helper()
	configDigest, err := h.Registry().PushBlob(t.Context(), repository, configBytes)
	require.NoError(t, err)
	layerDigest, err := h.Registry().PushBlob(t.Context(), repository, layerBytes)
	require.NoError(t, err)
	return putImageManifest(t, h, repository, reference, configBytes, configDigest, layerBytes, layerDigest)
}

func putImageManifest(
	t *testing.T,
	h *e2etest.Harness,
	repository string,
	reference string,
	configBytes []byte,
	configDigest digest.Digest,
	layerBytes []byte,
	layerDigest digest.Digest,
) pushedImage {
	t.Helper()
	manifestBytes, err := json.Marshal(imageManifest{
		SchemaVersion: 2,
		MediaType:     imageManifestMediaType,
		Config:        descriptor{MediaType: imageConfigMediaType, Digest: configDigest, Size: int64(len(configBytes))},
		Layers:        []descriptor{{MediaType: imageLayerMediaType, Digest: layerDigest, Size: int64(len(layerBytes))}},
	})
	require.NoError(t, err)
	manifestDigest := digest.FromBytes(manifestBytes)
	if reference == "" {
		reference = manifestDigest.String()
	}
	response, err := h.Registry().PutManifest(t.Context(), repository, reference, manifestBytes, imageManifestMediaType)
	require.NoError(t, err)
	assert.Equal(t, manifestDigest, response.Digest)
	return pushedImage{manifest: manifestBytes, digest: manifestDigest, config: configDigest, layer: layerDigest}
}

func pushArtifact(
	t *testing.T,
	h *e2etest.Harness,
	repository string,
	subject pushedImage,
	configBytes []byte,
	artifactType string,
	payload []byte,
) pushedArtifact {
	t.Helper()
	blobDigest, err := h.Registry().PushBlob(t.Context(), repository, payload)
	require.NoError(t, err)
	manifestBytes, err := json.Marshal(artifactManifest{
		SchemaVersion: 2,
		MediaType:     imageManifestMediaType,
		ArtifactType:  artifactType,
		Config: descriptor{
			MediaType: emptyConfigMediaType,
			Digest:    subject.config,
			Size:      int64(len(configBytes)),
		},
		Layers: []descriptor{{
			MediaType: artifactType,
			Digest:    blobDigest,
			Size:      int64(len(payload)),
		}},
		Subject: descriptor{
			MediaType: imageManifestMediaType,
			Digest:    subject.digest,
			Size:      int64(len(subject.manifest)),
		},
	})
	require.NoError(t, err)
	manifestDigest := digest.FromBytes(manifestBytes)
	response, err := h.Registry().PutManifest(t.Context(), repository, manifestDigest.String(), manifestBytes, imageManifestMediaType)
	require.NoError(t, err)
	assert.Equal(t, subject.digest, response.Subject)
	assert.Equal(t, manifestDigest, response.Digest)
	return pushedArtifact{manifest: manifestBytes, payload: payload, digest: manifestDigest, blob: blobDigest}
}

func assertRegistryMissing(t *testing.T, h *e2etest.Harness, repository, reference string) {
	t.Helper()
	_, err := h.Registry().GetManifest(t.Context(), repository, reference)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 404")
}

func assertBlobMissing(t *testing.T, h *e2etest.Harness, repository string, dgst digest.Digest) {
	t.Helper()
	_, err := h.Registry().GetBlob(t.Context(), repository, dgst)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 404")
}
