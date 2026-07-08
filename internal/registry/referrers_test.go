package registry

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
)

// --- mock store ---

type mockStore struct {
	repoID    int64
	repoErr   error
	referrers []oci.ReferrerRecord
	refErr    error

	lastSubject      digest.Digest
	lastArtifactType string
}

func (m *mockStore) GetRepositoryID(_ context.Context, _ oci.RepositoryName) (int64, error) {
	return m.repoID, m.repoErr
}

func (m *mockStore) ListReferrers(_ context.Context, _ int64, subject digest.Digest, artifactType string) ([]oci.ReferrerRecord, error) {
	m.lastSubject = subject
	m.lastArtifactType = artifactType
	return m.referrers, m.refErr
}

func (m *mockStore) EnsureRepository(context.Context, oci.RepositoryName) (int64, error) {
	return 0, nil
}
func (m *mockStore) PutManifest(context.Context, int64, oci.ManifestRecord) (int64, error) { //nolint:gocritic // interface compliance
	return 0, nil
}
func (m *mockStore) DeleteManifest(context.Context, int64, digest.Digest) error  { return nil }
func (m *mockStore) PutBlob(context.Context, oci.BlobRecord) (int64, error)      { return 0, nil }
func (m *mockStore) PutTag(context.Context, int64, oci.TagRecord) (int64, error) { return 0, nil }
func (m *mockStore) DeleteTag(context.Context, int64, string) error              { return nil }
func (m *mockStore) GetTagDigest(context.Context, int64, string) (digest.Digest, error) {
	return "", nil
}
func (m *mockStore) GetManifestDigest(context.Context, int64, digest.Digest) (digest.Digest, error) {
	return "", nil
}
func (m *mockStore) GetManifestContent(context.Context, digest.Digest) ([]byte, error) {
	return nil, nil
}
func (m *mockStore) BlobExists(context.Context, digest.Digest) (bool, error) { return false, nil }
func (m *mockStore) BlobLinkedToRepo(context.Context, int64, digest.Digest) (bool, error) {
	return false, nil
}
func (m *mockStore) ListTags(context.Context, int64) ([]string, error)              { return nil, nil }
func (m *mockStore) ListRepositories(context.Context) ([]oci.RepositoryName, error) { return nil, nil }
func (m *mockStore) PutUploadedBlob(context.Context, int64, digest.Digest) error    { return nil }
func (m *mockStore) DeleteUploadedBlob(context.Context, int64, digest.Digest) (int64, error) {
	return 0, nil
}
func (m *mockStore) CleanExpiredUploadedBlobs(context.Context) error { return nil }

// --- tests ---

func newTestHandler(store oci.MetadataStore) *ReferrersHandler {
	return &ReferrersHandler{
		store:  store,
		config: ReferrersConfig{LibraryNamespace: "library", AnonymousAccess: true},
	}
}

func TestReferrers_EmptyList(t *testing.T) {
	store := &mockStore{repoID: 1}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject-manifest")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String(), http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
	}
	if ct := w.Header().Get("Content-Type"); ct != ociImageIndexMediaType {
		t.Errorf("Content-Type = %q, want %q", ct, ociImageIndexMediaType)
	}

	var idx ociIndex
	if err := json.NewDecoder(w.Body).Decode(&idx); err != nil {
		t.Fatal(err)
	}
	if idx.SchemaVersion != 2 {
		t.Errorf("schemaVersion = %d, want 2", idx.SchemaVersion)
	}
	if idx.MediaType != ociImageIndexMediaType {
		t.Errorf("mediaType = %q, want %q", idx.MediaType, ociImageIndexMediaType)
	}
	if len(idx.Manifests) != 0 {
		t.Errorf("manifests = %d, want 0", len(idx.Manifests))
	}
}

func TestReferrers_WithResults(t *testing.T) {
	refDgst := digest.FromString("referrer-manifest")
	store := &mockStore{
		repoID: 1,
		referrers: []oci.ReferrerRecord{
			{
				Digest:       refDgst.String(),
				MediaType:    "application/vnd.oci.image.manifest.v1+json",
				ArtifactType: "application/vnd.example.sbom.v1",
				Size:         512,
			},
		},
	}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject-manifest")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String(), http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
	}

	var idx ociIndex
	if err := json.NewDecoder(w.Body).Decode(&idx); err != nil {
		t.Fatal(err)
	}
	if len(idx.Manifests) != 1 {
		t.Fatalf("manifests = %d, want 1", len(idx.Manifests))
	}
	m := idx.Manifests[0]
	if m.Digest != refDgst.String() {
		t.Errorf("digest = %s, want %s", m.Digest, refDgst)
	}
	if m.MediaType != "application/vnd.oci.image.manifest.v1+json" {
		t.Errorf("mediaType = %q, want oci manifest", m.MediaType)
	}
	if m.ArtifactType != "application/vnd.example.sbom.v1" {
		t.Errorf("artifactType = %q, want sbom", m.ArtifactType)
	}
	if m.Size != 512 {
		t.Errorf("size = %d, want 512", m.Size)
	}
}

func TestReferrers_ArtifactTypeFilter(t *testing.T) {
	store := &mockStore{repoID: 1}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String()+"?artifactType=application/vnd.example.sbom.v1", http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
	}
	if h := w.Header().Get("OCI-Filters-Applied"); h != "artifactType" {
		t.Errorf("OCI-Filters-Applied = %q, want %q", h, "artifactType")
	}
	if store.lastArtifactType != "application/vnd.example.sbom.v1" {
		t.Errorf("artifactType passed to store = %q, want sbom", store.lastArtifactType)
	}
}

func TestReferrers_NoFilterHeader_WhenNoFilter(t *testing.T) {
	store := &mockStore{repoID: 1}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String(), http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if h := w.Header().Get("OCI-Filters-Applied"); h != "" {
		t.Errorf("OCI-Filters-Applied = %q, want empty", h)
	}
}

func TestReferrers_InvalidDigest(t *testing.T) {
	store := &mockStore{repoID: 1}
	handler := newTestHandler(store)

	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/notadigest", http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestReferrers_RepoNotFound(t *testing.T) {
	store := &mockStore{
		repoErr: fmt.Errorf("get repository test: %w", oci.ErrNotExist),
	}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String(), http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusNotFound)
	}
}

func TestReferrers_RepoLookupError(t *testing.T) {
	store := &mockStore{
		repoErr: fmt.Errorf("db connection refused"),
	}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String(), http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusInternalServerError)
	}
}

func TestReferrers_Matches(t *testing.T) {
	handler := newTestHandler(&mockStore{})
	dgst := digest.FromString("test")

	tests := []struct {
		method string
		path   string
		want   bool
	}{
		{http.MethodGet, "/v2/ns/repo/referrers/" + dgst.String(), true},
		{http.MethodGet, "/v2/ns/sub/repo/referrers/" + dgst.String(), true},
		{http.MethodPost, "/v2/ns/repo/referrers/" + dgst.String(), false},
		{http.MethodGet, "/v2/ns/repo/manifests/" + dgst.String(), false},
		{http.MethodGet, "/v2/ns/repo/referrers/notadigest", true},
	}

	for _, tt := range tests {
		r := httptest.NewRequestWithContext(t.Context(), tt.method, tt.path, http.NoBody)
		if got := handler.Matches(r); got != tt.want {
			t.Errorf("Matches(%s %s) = %v, want %v", tt.method, tt.path, got, tt.want)
		}
	}
}

func TestReferrers_MultipleReferrers(t *testing.T) {
	ref1 := digest.FromString("referrer-1")
	ref2 := digest.FromString("referrer-2")
	store := &mockStore{
		repoID: 1,
		referrers: []oci.ReferrerRecord{
			{
				Digest:       ref1.String(),
				MediaType:    "application/vnd.oci.image.manifest.v1+json",
				ArtifactType: "application/vnd.example.sbom.v1",
				Size:         100,
			},
			{
				Digest:       ref2.String(),
				MediaType:    "application/vnd.oci.image.manifest.v1+json",
				ArtifactType: "application/vnd.example.signature.v1",
				Size:         200,
			},
		},
	}
	handler := newTestHandler(store)

	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/ns/repo/referrers/"+subjectDgst.String(), http.NoBody)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
	}

	var idx ociIndex
	if err := json.NewDecoder(w.Body).Decode(&idx); err != nil {
		t.Fatal(err)
	}
	if len(idx.Manifests) != 2 {
		t.Fatalf("manifests = %d, want 2", len(idx.Manifests))
	}
}

func TestReferrers_LibraryNamespace(t *testing.T) {
	store := &mockStore{repoID: 1}
	handler := newTestHandler(store)

	ns, repo := handler.splitName("myimage")
	if ns != "library" {
		t.Errorf("namespace = %q, want %q", ns, "library")
	}
	if repo != "myimage" {
		t.Errorf("repo = %q, want %q", repo, "myimage")
	}
}

func TestReferrers_NestedRepoName(t *testing.T) {
	store := &mockStore{repoID: 1}
	handler := newTestHandler(store)

	ns, repo := handler.splitName("org/team/image")
	if ns != "org" {
		t.Errorf("namespace = %q, want %q", ns, "org")
	}
	if repo != "team/image" {
		t.Errorf("repo = %q, want %q", repo, "team/image")
	}
}
