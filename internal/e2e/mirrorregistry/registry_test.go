package mirrorregistry_test

import (
	"encoding/json"
	"net/http"
	"net/url"
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
	emptyConfigMediaType   = "application/vnd.oci.empty.v1+json"
	artifactType           = "application/vnd.example.sbom.v1"
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

func TestRegistryReferrersLifecycle(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-referrers"

	configBytes := []byte(`{}`)
	layerBytes := []byte("subject layer")
	configDigest, err := h.Registry().PushBlob(ctx, repository, configBytes)
	require.NoError(t, err)
	layerDigest, err := h.Registry().PushBlob(ctx, repository, layerBytes)
	require.NoError(t, err)

	subjectBytes, err := json.Marshal(imageManifest{
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
	subjectResponse, err := h.Registry().PutManifest(ctx, repository, "subject", subjectBytes, imageManifestMediaType)
	require.NoError(t, err)
	subjectDigest := subjectResponse.Digest

	artifactBytes := []byte("artifact payload")
	artifactBlobDigest, err := h.Registry().PushBlob(ctx, repository, artifactBytes)
	require.NoError(t, err)
	referrerBytes, err := json.Marshal(artifactManifest{
		SchemaVersion: 2,
		MediaType:     imageManifestMediaType,
		ArtifactType:  artifactType,
		Config: descriptor{
			MediaType: emptyConfigMediaType,
			Digest:    configDigest,
			Size:      int64(len(configBytes)),
		},
		Layers: []descriptor{{
			MediaType: artifactType,
			Digest:    artifactBlobDigest,
			Size:      int64(len(artifactBytes)),
		}},
		Subject: descriptor{
			MediaType: imageManifestMediaType,
			Digest:    subjectDigest,
			Size:      int64(len(subjectBytes)),
		},
	})
	require.NoError(t, err)
	referrerResponse, err := h.Registry().PutManifest(ctx, repository, "sbom", referrerBytes, imageManifestMediaType)
	require.NoError(t, err)
	assert.Equal(t, subjectDigest, referrerResponse.Subject)
	referrerDigest := referrerResponse.Digest

	referrers, err := h.Registry().GetReferrers(ctx, repository, subjectDigest)
	require.NoError(t, err)
	require.Equal(t, 2, referrers.SchemaVersion)
	require.Equal(t, "application/vnd.oci.image.index.v1+json", referrers.MediaType)
	require.Len(t, referrers.Manifests, 1)
	assert.Equal(t, referrerDigest.String(), referrers.Manifests[0].Digest)
	assert.Equal(t, imageManifestMediaType, referrers.Manifests[0].MediaType)
	assert.Equal(t, int64(len(referrerBytes)), referrers.Manifests[0].Size)
	assert.Equal(t, artifactType, referrers.Manifests[0].ArtifactType)
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
	layer    digest.Digest
}

func pushUniqueImage(t *testing.T, h *e2etest.Harness, content string) pushedImage {
	t.Helper()
	ctx := t.Context()
	const repository = "admin/shared-name"
	configBytes := []byte(`{}`)
	configDigest, err := h.Registry().PushBlob(ctx, repository, configBytes)
	require.NoError(t, err)
	layer := []byte(content)
	layerDigest, err := h.Registry().PushBlob(ctx, repository, layer)
	require.NoError(t, err)
	manifestBytes, err := json.Marshal(imageManifest{
		SchemaVersion: 2,
		MediaType:     imageManifestMediaType,
		Config:        descriptor{MediaType: imageConfigMediaType, Digest: configDigest, Size: int64(len(configBytes))},
		Layers:        []descriptor{{MediaType: imageLayerMediaType, Digest: layerDigest, Size: int64(len(layer))}},
	})
	require.NoError(t, err)
	_, err = h.Registry().PutManifest(ctx, repository, "latest", manifestBytes, imageManifestMediaType)
	require.NoError(t, err)
	return pushedImage{manifest: manifestBytes, layer: layerDigest}
}
