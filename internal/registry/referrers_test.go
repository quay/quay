package registry

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/opencontainers/go-digest"
	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/oci"
	_ "modernc.org/sqlite"
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
		config: ReferrersConfig{LibraryNamespace: "library", AnonymousAccess: true, LibrarySupport: true},
	}
}

func TestNewReferrersHandlerConstructsDatabaseVerifier(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	handler := NewReferrersHandler(db, &mockStore{}, &ReferrersConfig{
		AnonymousAccess:                    true,
		LibrarySupport:                     true,
		DatabaseSecretKey:                  "test1234",
		RobotsDisallow:                     true,
		RobotsWhitelist:                    []string{"acme+deploy"},
		FeatureUserLastAccessed:            true,
		LastAccessedUpdateThresholdSeconds: 60,
	})

	if handler == nil {
		t.Fatal("expected handler")
	}
	if handler.authenticator == nil {
		t.Fatal("expected database-backed authenticator")
	}
	if handler.queries == nil {
		t.Fatal("expected database queries")
	}
	if handler.config.LibraryNamespace != defaultLibraryNamespace {
		t.Fatalf("library namespace = %q, want default %q", handler.config.LibraryNamespace, defaultLibraryNamespace)
	}
}

func setupReferrersAuthDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	db.SetMaxOpenConns(1)

	statements := []string{
		`CREATE TABLE "user" (id INTEGER PRIMARY KEY, uuid VARCHAR(36), username VARCHAR(255) NOT NULL, password_hash VARCHAR(255), email VARCHAR(255) NOT NULL, verified INTEGER NOT NULL DEFAULT 0, organization INTEGER NOT NULL DEFAULT 0, robot INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1, last_accessed DATETIME)`,
		`CREATE TABLE visibility (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL)`,
		`CREATE TABLE repository (id INTEGER PRIMARY KEY, namespace_user_id INTEGER, name VARCHAR(255) NOT NULL, visibility_id INTEGER NOT NULL, kind_id INTEGER NOT NULL DEFAULT 1, state INTEGER NOT NULL DEFAULT 0)`,
		`CREATE TABLE role (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL)`,
		`CREATE TABLE teamrole (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL)`,
		`CREATE TABLE team (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL, organization_id INTEGER NOT NULL, role_id INTEGER NOT NULL, description TEXT NOT NULL)`,
		`CREATE TABLE teammember (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, team_id INTEGER NOT NULL)`,
		`CREATE TABLE repositorypermission (id INTEGER PRIMARY KEY, team_id INTEGER, user_id INTEGER, repository_id INTEGER NOT NULL, role_id INTEGER NOT NULL)`,
		`CREATE TABLE repomirrorconfig (id INTEGER PRIMARY KEY, repository_id INTEGER NOT NULL, internal_robot_id INTEGER)`,
		`CREATE TABLE orgmirrorconfig (id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, internal_robot_id INTEGER)`,
		`CREATE TABLE orgmirrorrepository (id INTEGER PRIMARY KEY, org_mirror_config_id INTEGER NOT NULL, repository_id INTEGER)`,
		`INSERT INTO visibility (id, name) VALUES (1, 'public'), (2, 'private')`,
		`INSERT INTO role (id, name) VALUES (1, 'read'), (2, 'write'), (3, 'admin')`,
		`INSERT INTO teamrole (id, name) VALUES (1, 'admin'), (2, 'creator'), (3, 'member')`,
		`INSERT INTO "user" (id, uuid, username, password_hash, email, verified, organization, robot, enabled) VALUES (2, 'org-acme', 'acme', NULL, 'acme@example.com', 1, 1, 0, 1)`,
		`INSERT INTO repository (id, namespace_user_id, name, visibility_id, kind_id, state) VALUES (10, 2, 'private', 2, 1, 0)`,
	}
	for _, stmt := range statements {
		if _, err := db.ExecContext(t.Context(), stmt); err != nil {
			t.Fatalf("exec %q: %v", stmt, err)
		}
	}

	hash, err := bcrypt.GenerateFromPassword([]byte("correct-password"), bcrypt.MinCost)
	if err != nil {
		t.Fatalf("bcrypt: %v", err)
	}
	if _, err := db.ExecContext(t.Context(), `INSERT INTO "user" (id, uuid, username, password_hash, email, verified, organization, robot, enabled) VALUES (1, 'user-admin', 'admin', ?, 'admin@example.com', 1, 0, 0, 1)`, string(hash)); err != nil {
		t.Fatalf("insert admin: %v", err)
	}
	return db
}

func TestReferrers_AuthenticatedUserRequiresPullPermission(t *testing.T) {
	db := setupReferrersAuthDB(t)
	defer db.Close()

	handler := NewReferrersHandler(db, &mockStore{repoID: 10}, &ReferrersConfig{
		AnonymousAccess: false,
		LibrarySupport:  true,
	})
	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/acme/private/referrers/"+subjectDgst.String(), http.NoBody)
	req.SetBasicAuth("admin", "correct-password")
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusUnauthorized)
	}
}

func TestReferrers_AuthenticatedUserWithPullPermissionAllowed(t *testing.T) {
	db := setupReferrersAuthDB(t)
	defer db.Close()
	if _, err := db.ExecContext(t.Context(), `INSERT INTO repositorypermission (id, user_id, repository_id, role_id) VALUES (1, 1, 10, 1)`); err != nil {
		t.Fatalf("insert permission: %v", err)
	}

	handler := NewReferrersHandler(db, &mockStore{repoID: 10}, &ReferrersConfig{
		AnonymousAccess: false,
		LibrarySupport:  true,
	})
	subjectDgst := digest.FromString("subject")
	req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/v2/acme/private/referrers/"+subjectDgst.String(), http.NoBody)
	req.SetBasicAuth("admin", "correct-password")
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusOK)
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
