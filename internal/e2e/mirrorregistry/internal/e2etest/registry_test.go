package e2etest

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"

	"github.com/opencontainers/go-digest"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestResolveLocationOnlyAllowsRegistryOrigin(t *testing.T) {
	client := newRegistryClient("https://registry.example.test:5000", http.DefaultClient, "admin", "password")

	resolved, err := client.resolveLocation("/v2/admin/repo/blobs/uploads/upload-id")
	require.NoError(t, err)
	assert.Equal(t, "https://registry.example.test:5000/v2/admin/repo/blobs/uploads/upload-id", resolved)

	resolved, err = client.resolveLocation("https://registry.example.test:5000/v2/admin/repo/blobs/uploads/upload-id")
	require.NoError(t, err)
	assert.Equal(t, "https://registry.example.test:5000/v2/admin/repo/blobs/uploads/upload-id", resolved)

	_, err = client.resolveLocation("https://attacker.example.test/v2/admin/repo/blobs/uploads/upload-id")
	assert.ErrorContains(t, err, "does not match registry origin")

	_, err = client.resolveLocation("//attacker.example.test/v2/admin/repo/blobs/uploads/upload-id")
	assert.ErrorContains(t, err, "does not match registry origin")
}

func TestTokenIsReusedWithinRepositoryAndScope(t *testing.T) {
	var tokenRequests atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v2/auth" {
			http.NotFound(w, r)
			return
		}
		requestNumber := tokenRequests.Add(1)
		_, _ = fmt.Fprintf(w, `{"token":"token-%d"}`, requestNumber)
	}))
	t.Cleanup(server.Close)

	client := newRegistryClient(server.URL, server.Client(), "admin", "password")
	ctx := t.Context()

	pullToken, err := client.token(ctx, "admin/repo", "pull")
	require.NoError(t, err)
	repeatedPullToken, err := client.token(ctx, "admin/repo", "pull")
	require.NoError(t, err)
	assert.Equal(t, pullToken, repeatedPullToken)

	otherRepositoryToken, err := client.token(ctx, "admin/other-repo", "pull")
	require.NoError(t, err)
	assert.NotEqual(t, pullToken, otherRepositoryToken)

	pushToken, err := client.token(ctx, "admin/repo", "pull", "push")
	require.NoError(t, err)
	repeatedPushToken, err := client.token(ctx, "admin/repo", "pull", "push")
	require.NoError(t, err)
	assert.Equal(t, pushToken, repeatedPushToken)
	assert.NotEqual(t, pullToken, pushToken)

	assert.Equal(t, int32(3), tokenRequests.Load())
}

func TestGetBlobRejectsDigestMismatch(t *testing.T) {
	const repository = "admin/repo"
	expected := digest.FromString("expected content")
	body := []byte("unexpected content")
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v2/auth":
			_, _ = fmt.Fprint(w, `{"token":"token"}`)
		case "/v2/" + repository + "/blobs/" + expected.String():
			_, _ = w.Write(body)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(server.Close)

	client := newRegistryClient(server.URL, server.Client(), "test-user", "password")
	got, err := client.GetBlob(t.Context(), repository, expected)

	assert.Nil(t, got)
	assert.EqualError(t, err, fmt.Sprintf("blob response digest %q, want %q", digest.FromBytes(body), expected))
}
