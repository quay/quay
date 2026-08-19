package mirrorregistry_test

import (
	"errors"
	"io"
	"net/http"
	"sync"
	"testing"

	"github.com/opencontainers/go-digest"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/e2e/mirrorregistry/internal/e2etest"
)

func TestRegistryChunkedResumableBlobUpload(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-chunked-upload"
	chunks := [][]byte{
		[]byte("first chunk-"),
		[]byte("second chunk"),
	}
	content := append(append([]byte(nil), chunks[0]...), chunks[1]...)

	dgst, err := h.Registry().PushBlobChunked(t.Context(), repository, chunks...)
	require.NoError(t, err)
	assert.Equal(t, digest.FromBytes(content), dgst)

	got, err := h.Registry().GetBlob(t.Context(), repository, dgst)
	require.NoError(t, err)
	assert.Equal(t, content, got)
}

func TestRegistryBlobHeadAndDelete(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-blob-delete"
	content := []byte("head and delete blob")
	dgst, err := h.Registry().PushBlob(t.Context(), repository, content)
	require.NoError(t, err)

	metadata, err := h.Registry().HeadBlob(t.Context(), repository, dgst)
	require.NoError(t, err)
	assert.Equal(t, dgst, metadata.Digest)
	assert.Equal(t, int64(len(content)), metadata.Size)

	require.NoError(t, h.Registry().DeleteBlob(t.Context(), repository, dgst))
	assertBlobMissing(t, h, repository, dgst)
	_, err = h.Registry().HeadBlob(t.Context(), repository, dgst)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 404")
}

func TestRegistryRejectsBlobDigestMismatch(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-digest-mismatch"
	content := []byte("actual blob content")
	actual := digest.FromBytes(content)
	requested := digest.FromString("different blob content")

	_, err := h.Registry().PutBlobMonolithic(t.Context(), repository, content, requested)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 400")
	assert.Contains(t, err.Error(), "DIGEST_INVALID")
	assertBlobMissing(t, h, repository, requested)
	assertBlobMissing(t, h, repository, actual)
}

func TestRegistryTagPagination(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-tag-pagination"
	image := pushImage(t, h, repository, "alpha", []byte(`{}`), []byte("pagination layer"))
	for _, tag := range []string{"beta", "gamma"} {
		response, err := h.Registry().PutManifest(t.Context(), repository, tag, image.manifest, v1.MediaTypeImageManifest)
		require.NoError(t, err)
		assert.Equal(t, image.digest, response.Digest)
	}

	first, err := h.Registry().ListTagsPage(t.Context(), repository, 2, "")
	require.NoError(t, err)
	assert.Equal(t, repository, first.Name)
	assert.Equal(t, []string{"alpha", "beta"}, first.Tags)
	assert.Contains(t, first.Link, "last=beta")
	assert.Contains(t, first.Link, "n=2")
	assert.Contains(t, first.Link, `rel="next"`)

	second, err := h.Registry().ListTagsPage(t.Context(), repository, 2, "beta")
	require.NoError(t, err)
	assert.Equal(t, repository, second.Name)
	assert.Equal(t, []string{"gamma"}, second.Tags)
	assert.Empty(t, second.Link)
}

func TestRegistryConcurrentSameTagPushes(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const (
		repository       = "admin/e2e-concurrent-tag"
		concurrentPushes = 50
	)
	image := pushImage(t, h, repository, "v1", []byte(`{}`), []byte("concurrent tag layer"))
	token, err := h.Registry().RequestToken(ctx, repository, "pull", "push")
	require.NoError(t, err)

	start := make(chan struct{})
	pushErrors := make(chan error, concurrentPushes)
	var workers sync.WaitGroup
	workers.Add(concurrentPushes)
	for range concurrentPushes {
		go func() {
			defer workers.Done()
			<-start
			_, err := h.Registry().PutManifestWithToken(ctx, repository, "v1", image.manifest, v1.MediaTypeImageManifest, token)
			pushErrors <- err
		}()
	}

	close(start)
	workers.Wait()
	close(pushErrors)

	var failures []error
	for err := range pushErrors {
		if err != nil {
			failures = append(failures, err)
		}
	}
	require.NoError(t, errors.Join(failures...))

	lastWriter := pushImage(t, h, repository, "v1", []byte(`{"generation":"last"}`), []byte("last writer layer"))
	pulled, err := h.Registry().GetManifest(ctx, repository, "v1")
	require.NoError(t, err)
	assert.Equal(t, lastWriter.digest, pulled.Digest)
	assert.Equal(t, lastWriter.manifest, pulled.Body)
}

func TestRegistryCatalogIsRejected(t *testing.T) {
	h := e2etest.New(t)
	req, err := http.NewRequestWithContext(t.Context(), http.MethodGet, h.BaseURL()+"/v2/_catalog", http.NoBody)
	require.NoError(t, err)
	req.SetBasicAuth("admin", "e2e-password")

	resp, err := h.HTTPClient().Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
	assert.Contains(t, string(body), "UNAUTHORIZED")
	challenge := resp.Header.Get("WWW-Authenticate")
	assert.Contains(t, challenge, "Bearer")
	assert.Contains(t, challenge, `scope="registry:catalog:*"`)
}

func TestRegistryManifestContentTypeNegotiation(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-content-negotiation"
	image := pushImage(t, h, repository, "latest", []byte(`{}`), []byte("negotiated layer"))

	manifest, err := h.Registry().GetManifestWithAccept(t.Context(), repository, "latest", v1.MediaTypeImageManifest)
	require.NoError(t, err)
	assert.Equal(t, image.manifest, manifest.Body)
	assert.Equal(t, v1.MediaTypeImageManifest, manifest.MediaType)

	_, err = h.Registry().GetManifestWithAccept(t.Context(), repository, "latest", v1.MediaTypeImageIndex)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 404")
	assert.Contains(t, err.Error(), "MANIFEST_UNKNOWN")
}

func TestRegistryInvalidDigestReferenceReturnsNotFound(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-invalid-reference"
	pushImage(t, h, repository, "latest", []byte(`{}`), []byte("invalid reference layer"))

	_, err := h.Registry().GetManifest(t.Context(), repository, "sha256:not-a-digest")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 404")
	assert.NotContains(t, err.Error(), "HTTP 500")
}

func TestRegistryMonolithicBlobUpload(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-monolithic-upload"
	content := []byte("single PUT blob content")
	expected := digest.FromBytes(content)

	dgst, err := h.Registry().PutBlobMonolithic(t.Context(), repository, content, expected)
	require.NoError(t, err)
	assert.Equal(t, expected, dgst)
	got, err := h.Registry().GetBlob(t.Context(), repository, dgst)
	require.NoError(t, err)
	assert.Equal(t, content, got)
}
