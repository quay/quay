package e2etest

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/opencontainers/go-digest"
)

const (
	healthTimeout = 5 * time.Second
	clientTimeout = 10 * time.Second
)

// RegistryClient is a deliberately small HTTP client for the registry
// operations covered by the E2E suite. It performs token exchange explicitly
// rather than hiding authentication in a transport retry loop.
type RegistryClient struct {
	baseURL  string
	service  string
	client   *http.Client
	username string
	password string
}

// ManifestResponse contains an HTTP manifest response and its registry
// metadata.
type ManifestResponse struct {
	Body      []byte
	Digest    digest.Digest
	MediaType string
}

// Descriptor is an OCI descriptor returned by the referrers endpoint.
type Descriptor struct {
	MediaType    string `json:"mediaType"`
	Digest       string `json:"digest"`
	Size         int64  `json:"size"`
	ArtifactType string `json:"artifactType,omitempty"`
}

// ReferrersResponse is the subset of an OCI image index needed by the E2E
// referrers assertion.
type ReferrersResponse struct {
	SchemaVersion int          `json:"schemaVersion"`
	MediaType     string       `json:"mediaType"`
	Manifests     []Descriptor `json:"manifests"`
}

func newRegistryClient(baseURL string, client *http.Client, username, password string) *RegistryClient {
	parsed, err := url.Parse(baseURL)
	if err != nil || parsed.Host == "" {
		panic(fmt.Sprintf("invalid E2E registry URL %q", baseURL))
	}
	return &RegistryClient{
		baseURL:  strings.TrimRight(baseURL, "/"),
		service:  parsed.Host,
		client:   client,
		username: username,
		password: password,
	}
}

func (c *RegistryClient) token(ctx context.Context, repository string, actions ...string) (string, error) {
	if len(actions) == 0 {
		return "", fmt.Errorf("token request requires at least one action")
	}

	endpoint, err := url.Parse(c.baseURL + "/v2/auth")
	if err != nil {
		return "", err
	}
	query := endpoint.Query()
	query.Set("service", c.service)
	query.Set("scope", "repository:"+repository+":"+strings.Join(actions, ","))
	endpoint.RawQuery = query.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), http.NoBody)
	if err != nil {
		return "", err
	}
	req.SetBasicAuth(c.username, c.password)
	resp, err := c.client.Do(req) //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return "", err
	}
	body, readErr := readBody(resp)
	if readErr != nil {
		return "", readErr
	}
	if resp.StatusCode != http.StatusOK {
		return "", responseError(resp, body)
	}

	var tokenResponse struct {
		Token       string `json:"token"`
		AccessToken string `json:"access_token"`
	}
	if err := json.Unmarshal(body, &tokenResponse); err != nil {
		return "", fmt.Errorf("decode token response: %w", err)
	}
	if tokenResponse.Token == "" {
		tokenResponse.Token = tokenResponse.AccessToken
	}
	if tokenResponse.Token == "" {
		return "", fmt.Errorf("token response did not contain a token")
	}
	return tokenResponse.Token, nil
}

// PushBlob uploads content through the standard POST/PATCH/PUT upload flow.
func (c *RegistryClient) PushBlob(ctx context.Context, repository string, content []byte) (digest.Digest, error) {
	token, err := c.token(ctx, repository, "pull", "push")
	if err != nil {
		return "", err
	}
	location, err := c.startBlobUpload(ctx, repository, token)
	if err != nil {
		return "", err
	}
	location, err = c.appendBlobUpload(ctx, location, token, content)
	if err != nil {
		return "", err
	}
	return c.finishBlobUpload(ctx, location, token, content)
}

func (c *RegistryClient) startBlobUpload(ctx context.Context, repository, token string) (string, error) {
	resp, err := c.do(ctx, http.MethodPost, c.endpoint(repository, "/blobs/uploads/"), token, nil, "") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return "", err
	}
	body, err := readBody(resp)
	if err != nil {
		return "", err
	}
	if resp.StatusCode != http.StatusAccepted {
		return "", responseError(resp, body)
	}
	return c.resolveLocation(resp.Header.Get("Location"))
}

func (c *RegistryClient) appendBlobUpload(ctx context.Context, location, token string, content []byte) (string, error) {
	resp, err := c.do(ctx, http.MethodPatch, location, token, content, "application/octet-stream") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return "", err
	}
	body, err := readBody(resp)
	if err != nil {
		return "", err
	}
	if resp.StatusCode != http.StatusAccepted {
		return "", responseError(resp, body)
	}
	if next := resp.Header.Get("Location"); next != "" {
		return c.resolveLocation(next)
	}
	return location, nil
}

func (c *RegistryClient) finishBlobUpload(ctx context.Context, location, token string, content []byte) (digest.Digest, error) {
	dgst := digest.FromBytes(content)
	finish, err := url.Parse(location)
	if err != nil {
		return "", fmt.Errorf("parse upload location: %w", err)
	}
	query := finish.Query()
	query.Set("digest", dgst.String())
	finish.RawQuery = query.Encode()
	resp, err := c.do(ctx, http.MethodPut, finish.String(), token, nil, "") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return "", err
	}
	body, err := readBody(resp)
	if err != nil {
		return "", err
	}
	if resp.StatusCode != http.StatusCreated {
		return "", responseError(resp, body)
	}
	if got := resp.Header.Get("Docker-Content-Digest"); got != "" && got != dgst.String() {
		return "", fmt.Errorf("blob response digest %q, want %q", got, dgst)
	}
	return dgst, nil
}

// PutManifest stores a manifest under tag and returns its content digest.
func (c *RegistryClient) PutManifest(ctx context.Context, repository, tag string, content []byte, mediaType string) (digest.Digest, error) {
	token, err := c.token(ctx, repository, "pull", "push")
	if err != nil {
		return "", err
	}
	resp, err := c.do(ctx, http.MethodPut, c.endpoint(repository, "/manifests/"+tag), token, content, mediaType) //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return "", err
	}
	body, err := readBody(resp)
	if err != nil {
		return "", err
	}
	if resp.StatusCode != http.StatusCreated {
		return "", responseError(resp, body)
	}
	got := resp.Header.Get("Docker-Content-Digest")
	if got == "" {
		return "", fmt.Errorf("manifest response did not contain Docker-Content-Digest")
	}
	dgst, err := digest.Parse(got)
	if err != nil {
		return "", fmt.Errorf("parse manifest response digest: %w", err)
	}
	return dgst, nil
}

// HeadManifest fetches manifest headers without a response body.
func (c *RegistryClient) HeadManifest(ctx context.Context, repository, reference string) (ManifestResponse, error) {
	token, err := c.token(ctx, repository, "pull")
	if err != nil {
		return ManifestResponse{}, err
	}
	resp, err := c.do(ctx, http.MethodHead, c.endpoint(repository, "/manifests/"+reference), token, nil, "", manifestMediaTypes) //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return ManifestResponse{}, err
	}
	body, err := readBody(resp)
	if err != nil {
		return ManifestResponse{}, err
	}
	if resp.StatusCode != http.StatusOK {
		return ManifestResponse{}, responseError(resp, body)
	}
	return manifestResponse(resp, nil)
}

// GetManifest fetches a manifest by tag or digest.
func (c *RegistryClient) GetManifest(ctx context.Context, repository, reference string) (ManifestResponse, error) {
	token, err := c.token(ctx, repository, "pull")
	if err != nil {
		return ManifestResponse{}, err
	}
	resp, err := c.do(ctx, http.MethodGet, c.endpoint(repository, "/manifests/"+reference), token, nil, "", manifestMediaTypes) //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return ManifestResponse{}, err
	}
	body, err := readBody(resp)
	if err != nil {
		return ManifestResponse{}, err
	}
	if resp.StatusCode != http.StatusOK {
		return ManifestResponse{}, responseError(resp, body)
	}
	return manifestResponse(resp, body)
}

// GetBlob fetches a blob by digest.
func (c *RegistryClient) GetBlob(ctx context.Context, repository string, dgst digest.Digest) ([]byte, error) {
	token, err := c.token(ctx, repository, "pull")
	if err != nil {
		return nil, err
	}
	resp, err := c.do(ctx, http.MethodGet, c.endpoint(repository, "/blobs/"+dgst.String()), token, nil, "") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return nil, err
	}
	body, err := readBody(resp)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, responseError(resp, body)
	}
	return body, nil
}

// ListTags returns all tags currently associated with a repository.
func (c *RegistryClient) ListTags(ctx context.Context, repository string) ([]string, error) {
	token, err := c.token(ctx, repository, "pull")
	if err != nil {
		return nil, err
	}
	resp, err := c.do(ctx, http.MethodGet, c.endpoint(repository, "/tags/list"), token, nil, "") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return nil, err
	}
	body, err := readBody(resp)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, responseError(resp, body)
	}
	var response struct {
		Tags []string `json:"tags"`
	}
	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("decode tag response: %w", err)
	}
	return response.Tags, nil
}

// GetReferrers fetches the OCI referrers index for a subject digest.
func (c *RegistryClient) GetReferrers(ctx context.Context, repository string, subject digest.Digest) (ReferrersResponse, error) {
	token, err := c.token(ctx, repository, "pull")
	if err != nil {
		return ReferrersResponse{}, err
	}
	resp, err := c.do(ctx, http.MethodGet, c.endpoint(repository, "/referrers/"+subject.String()), token, nil, "") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return ReferrersResponse{}, err
	}
	body, err := readBody(resp)
	if err != nil {
		return ReferrersResponse{}, err
	}
	if resp.StatusCode != http.StatusOK {
		return ReferrersResponse{}, responseError(resp, body)
	}
	var response ReferrersResponse
	if err := json.Unmarshal(body, &response); err != nil {
		return ReferrersResponse{}, fmt.Errorf("decode referrers response: %w", err)
	}
	return response, nil
}

// DeleteManifest deletes a manifest by digest.
func (c *RegistryClient) DeleteManifest(ctx context.Context, repository string, dgst digest.Digest) error {
	token, err := c.token(ctx, repository, "pull", "push")
	if err != nil {
		return err
	}
	resp, err := c.do(ctx, http.MethodDelete, c.endpoint(repository, "/manifests/"+dgst.String()), token, nil, "") //nolint:bodyclose // readBody closes every response body
	if err != nil {
		return err
	}
	body, err := readBody(resp)
	if err != nil {
		return err
	}
	if resp.StatusCode != http.StatusAccepted {
		return responseError(resp, body)
	}
	return nil
}

func (c *RegistryClient) endpoint(repository, suffix string) string {
	return c.baseURL + "/v2/" + repository + suffix
}

func (c *RegistryClient) do(ctx context.Context, method, endpoint, token string, body []byte, contentType string, accept ...string) (*http.Response, error) {
	var reader io.Reader = http.NoBody
	if body != nil {
		reader = bytes.NewReader(body)
	}
	req, err := http.NewRequestWithContext(ctx, method, endpoint, reader)
	if err != nil {
		return nil, err
	}
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	if len(accept) > 0 {
		req.Header.Set("Accept", strings.Join(accept, ", "))
	}
	return c.client.Do(req)
}

func (c *RegistryClient) resolveLocation(location string) (string, error) {
	if location == "" {
		return "", fmt.Errorf("registry response did not contain an upload Location")
	}
	parsed, err := url.Parse(location)
	if err != nil {
		return "", fmt.Errorf("parse upload Location: %w", err)
	}
	if parsed.IsAbs() {
		return parsed.String(), nil
	}
	base, err := url.Parse(c.baseURL + "/")
	if err != nil {
		return "", err
	}
	return base.ResolveReference(parsed).String(), nil
}

const manifestMediaTypes = "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"

func manifestResponse(resp *http.Response, body []byte) (ManifestResponse, error) {
	rawDigest := resp.Header.Get("Docker-Content-Digest")
	dgst, err := digest.Parse(rawDigest)
	if err != nil {
		return ManifestResponse{}, fmt.Errorf("parse manifest digest %q: %w", rawDigest, err)
	}
	return ManifestResponse{
		Body:      body,
		Digest:    dgst,
		MediaType: resp.Header.Get("Content-Type"),
	}, nil
}

func readBody(resp *http.Response) ([]byte, error) {
	defer func() { _ = resp.Body.Close() }()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read HTTP response body: %w", err)
	}
	return body, nil
}

func responseError(resp *http.Response, body []byte) error {
	return fmt.Errorf("registry returned HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
}
