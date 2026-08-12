package mirrorregistry_test

import (
	"io"
	"net/http"
	"net/url"
	"testing"

	v1 "github.com/opencontainers/image-spec/specs-go/v1"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/e2e/mirrorregistry/internal/e2etest"
)

func TestRegistryAuthChallengeWithoutCredentials(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-auth-challenge"

	response := registryRequest(t, h, http.MethodGet, repository+"/manifests/latest", "")
	assert.Equal(t, http.StatusUnauthorized, response.status)

	parsedURL, err := url.Parse(h.BaseURL())
	require.NoError(t, err)
	challenge := response.headers.Get("WWW-Authenticate")
	assert.Contains(t, challenge, `Bearer realm="`+h.BaseURL()+`/v2/auth"`)
	assert.Contains(t, challenge, `service="`+parsedURL.Host+`"`)
	assert.Contains(t, challenge, `scope="repository:`+repository+`:pull"`)
	assert.NotContains(t, challenge, `error=`)
}

func TestRegistryRejectsGarbageBearerToken(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-auth-garbage"

	response := registryRequest(t, h, http.MethodGet, repository+"/manifests/latest", "not-a-token")
	assert.Equal(t, http.StatusUnauthorized, response.status)
	assert.Contains(t, response.headers.Get("WWW-Authenticate"), `error="invalid_token"`)
}

func TestRegistryRejectsExpiredBearerToken(t *testing.T) {
	h := e2etest.New(t)
	const repository = "admin/e2e-auth-expired"

	token, err := h.ExpiredToken("admin", repository, "pull")
	require.NoError(t, err)
	response := registryRequest(t, h, http.MethodGet, repository+"/manifests/latest", token)
	assert.Equal(t, http.StatusUnauthorized, response.status)
	assert.Contains(t, response.headers.Get("WWW-Authenticate"), `error="invalid_token"`)
}

func TestRegistryInsufficientScopeChallenge(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()
	const repository = "admin/e2e-auth-insufficient-scope"

	pullToken, err := h.Registry().RequestToken(ctx, repository, "pull")
	require.NoError(t, err)
	response := registryRequest(t, h, http.MethodPost, repository+"/blobs/uploads/", pullToken)
	assert.Equal(t, http.StatusUnauthorized, response.status)
	challenge := response.headers.Get("WWW-Authenticate")
	assert.Contains(t, challenge, `scope="repository:`+repository+`:pull,push"`)
	assert.Contains(t, challenge, `error="insufficient_scope"`)
}

func TestRegistryTokenRequestRejectsMismatchedAccount(t *testing.T) {
	h := e2etest.New(t)
	ctx := t.Context()

	_, err := h.Registry().RequestTokenWithCredentials(ctx, e2etest.E2EUsername, e2etest.E2EPassword, "somebody-else", "repository:admin/e2e-auth-account:pull")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "HTTP 401")
}

type registryResponse struct {
	status  int
	headers http.Header
	body    []byte
}

func registryRequest(t *testing.T, h *e2etest.Harness, method, path, token string) registryResponse {
	t.Helper()
	req, err := http.NewRequestWithContext(t.Context(), method, h.BaseURL()+"/v2/"+path, http.NoBody)
	require.NoError(t, err)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	req.Header.Set("Accept", v1.MediaTypeImageManifest+", "+v1.MediaTypeImageIndex)
	resp, err := h.HTTPClient().Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	responseBody, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	return registryResponse{status: resp.StatusCode, headers: resp.Header.Clone(), body: responseBody}
}
