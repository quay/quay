package middleware

import (
	"context"
	"errors"
	"testing"

	"github.com/distribution/distribution/v3"
	"github.com/distribution/reference"
	"github.com/opencontainers/go-digest"
	v1 "github.com/opencontainers/image-spec/specs-go/v1"

	"github.com/quay/quay/internal/oci"
)

// --- mock store ---

type mockStore struct {
	ensureRepoID  int64
	ensureRepoErr error

	lastRepoID int64

	putManifestID  int64
	putManifestErr error
	putManifestRec oci.ManifestRecord

	deleteManifestErr  error
	deleteManifestDgst digest.Digest

	putBlobID  int64
	putBlobErr error
	putBlobRec oci.BlobRecord

	putTagID  int64
	putTagErr error
	putTagRec oci.TagRecord

	deleteTagErr  error
	deleteTagName string
}

func (m *mockStore) EnsureRepository(_ context.Context, _ oci.RepositoryName) (int64, error) {
	return m.ensureRepoID, m.ensureRepoErr
}

func (m *mockStore) PutManifest(_ context.Context, repoID int64, r oci.ManifestRecord) (int64, error) { //nolint:gocritic // interface compliance
	m.lastRepoID = repoID
	m.putManifestRec = r
	return m.putManifestID, m.putManifestErr
}

func (m *mockStore) DeleteManifest(_ context.Context, repoID int64, dgst digest.Digest) error {
	m.lastRepoID = repoID
	m.deleteManifestDgst = dgst
	return m.deleteManifestErr
}

func (m *mockStore) PutBlob(_ context.Context, b oci.BlobRecord) (int64, error) {
	m.putBlobRec = b
	return m.putBlobID, m.putBlobErr
}

func (m *mockStore) PutTag(_ context.Context, repoID int64, t oci.TagRecord) (int64, error) {
	m.lastRepoID = repoID
	m.putTagRec = t
	return m.putTagID, m.putTagErr
}

func (m *mockStore) DeleteTag(_ context.Context, repoID int64, tag string) error {
	m.lastRepoID = repoID
	m.deleteTagName = tag
	return m.deleteTagErr
}

func (m *mockStore) GetRepositoryID(_ context.Context, _ oci.RepositoryName) (int64, error) {
	return 0, errNotImplemented
}

func (m *mockStore) GetTagDigest(_ context.Context, _ int64, _ string) (digest.Digest, error) {
	return "", errNotImplemented
}

func (m *mockStore) GetManifestDigest(_ context.Context, _ int64, _ digest.Digest) (digest.Digest, error) {
	return "", errNotImplemented
}

func (m *mockStore) GetManifestContent(_ context.Context, _ digest.Digest) ([]byte, error) {
	return nil, errNotImplemented
}

func (m *mockStore) BlobExists(_ context.Context, _ digest.Digest) (bool, error) {
	return false, errNotImplemented
}

func (m *mockStore) BlobLinkedToRepo(_ context.Context, _ int64, _ digest.Digest) (bool, error) {
	return false, errNotImplemented
}

func (m *mockStore) ListTags(_ context.Context, _ int64) ([]string, error) {
	return nil, errNotImplemented
}

func (m *mockStore) ListRepositories(_ context.Context) ([]oci.RepositoryName, error) {
	return nil, errNotImplemented
}

func (m *mockStore) PutUploadedBlob(_ context.Context, _ int64, _ digest.Digest) error {
	return nil
}

func (m *mockStore) CleanExpiredUploadedBlobs(_ context.Context) error {
	return errNotImplemented
}

var errNotImplemented = errors.New("mock: not implemented")

// --- mock distribution types ---

type mockManifest struct {
	mediaType  string
	payload    []byte
	references []v1.Descriptor
}

func (m *mockManifest) References() []v1.Descriptor { return m.references }
func (m *mockManifest) Payload() (string, []byte, error) { //nolint:gocritic // interface compliance
	return m.mediaType, m.payload, nil
}

type mockManifestService struct {
	putDigest digest.Digest
	putErr    error
	deleteErr error
}

func (ms *mockManifestService) Exists(_ context.Context, _ digest.Digest) (bool, error) {
	return true, nil
}

func (ms *mockManifestService) Get(_ context.Context, _ digest.Digest, _ ...distribution.ManifestServiceOption) (distribution.Manifest, error) { //nolint:gocritic // interface compliance
	return nil, errNotImplemented
}

func (ms *mockManifestService) Put(_ context.Context, _ distribution.Manifest, _ ...distribution.ManifestServiceOption) (digest.Digest, error) {
	return ms.putDigest, ms.putErr
}

func (ms *mockManifestService) Delete(_ context.Context, _ digest.Digest) error {
	return ms.deleteErr
}

type mockTagService struct {
	tagErr   error
	untagErr error
}

func (ts *mockTagService) Get(_ context.Context, _ string) (v1.Descriptor, error) {
	return v1.Descriptor{}, nil
}

func (ts *mockTagService) Tag(_ context.Context, _ string, _ v1.Descriptor) error { //nolint:gocritic // interface compliance
	return ts.tagErr
}

func (ts *mockTagService) Untag(_ context.Context, _ string) error {
	return ts.untagErr
}

func (ts *mockTagService) All(_ context.Context) ([]string, error) {
	return nil, nil
}

func (ts *mockTagService) Lookup(_ context.Context, _ v1.Descriptor) ([]string, error) { //nolint:gocritic // interface compliance
	return nil, nil
}

type mockBlobStore struct {
	distribution.BlobStore
	putDesc   v1.Descriptor
	putErr    error
	createWr  distribution.BlobWriter
	createErr error
}

func (bs *mockBlobStore) Put(_ context.Context, _ string, _ []byte) (v1.Descriptor, error) {
	return bs.putDesc, bs.putErr
}

func (bs *mockBlobStore) Create(_ context.Context, _ ...distribution.BlobCreateOption) (distribution.BlobWriter, error) {
	return bs.createWr, bs.createErr
}

type mockBlobWriter struct {
	distribution.BlobWriter
	commitDesc v1.Descriptor
	commitErr  error
}

func (bw *mockBlobWriter) Commit(_ context.Context, _ v1.Descriptor) (v1.Descriptor, error) { //nolint:gocritic // interface compliance
	return bw.commitDesc, bw.commitErr
}

// --- helpers ---

type fakeDistRepo struct {
	distribution.Repository
	name reference.Named
	ms   *mockManifestService
	bs   *mockBlobStore
	ts   *mockTagService
}

func (r *fakeDistRepo) Named() reference.Named { return r.name }
func (r *fakeDistRepo) Manifests(_ context.Context, _ ...distribution.ManifestServiceOption) (distribution.ManifestService, error) {
	return r.ms, nil
}
func (r *fakeDistRepo) Blobs(_ context.Context) distribution.BlobStore { return r.bs }
func (r *fakeDistRepo) Tags(_ context.Context) distribution.TagService { return r.ts }

// --- tests ---

func TestManifestPut_RecordsMetadata(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putManifestID: 10}
	dgst := digest.FromString("test-manifest")

	innerMS := &mockManifestService{putDigest: dgst}
	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ms:   innerMS,
	}

	repo := newRepository(innerRepo, store, "library")
	ms, err := repo.Manifests(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	manifest := &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{"schemaVersion":2}`),
		references: []v1.Descriptor{
			{Digest: digest.FromString("layer1"), Size: 100},
		},
	}

	got, err := ms.Put(context.Background(), manifest)
	if err != nil {
		t.Fatal(err)
	}
	if got != dgst {
		t.Errorf("digest = %s, want %s", got, dgst)
	}
	if store.putManifestRec.Digest != dgst {
		t.Errorf("stored digest = %s, want %s", store.putManifestRec.Digest, dgst)
	}
	if len(store.putManifestRec.BlobDigests) != 1 {
		t.Errorf("blob refs = %d, want 1", len(store.putManifestRec.BlobDigests))
	}
	if store.lastRepoID != 1 {
		t.Errorf("repoID = %d, want 1", store.lastRepoID)
	}
}

func TestManifestPut_WithTag(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putManifestID: 10}
	dgst := digest.FromString("tagged-manifest")

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ms:   &mockManifestService{putDigest: dgst},
	}
	repo := newRepository(innerRepo, store, "library")
	ms, err := repo.Manifests(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	manifest := &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{}`),
	}

	_, err = ms.Put(context.Background(), manifest, distribution.WithTag("v1"))
	if err != nil {
		t.Fatal(err)
	}
	if store.putManifestRec.Tag != "v1" {
		t.Errorf("tag = %q, want %q", store.putManifestRec.Tag, "v1")
	}
}

func TestManifestPut_IndexClassifiesChildDigests(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putManifestID: 10}
	dgst := digest.FromString("index")

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ms:   &mockManifestService{putDigest: dgst},
	}
	repo := newRepository(innerRepo, store, "library")
	ms, err := repo.Manifests(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	childDgst := digest.FromString("child")
	manifest := &mockManifest{
		mediaType:  "application/vnd.oci.image.index.v1+json",
		payload:    []byte(`{}`),
		references: []v1.Descriptor{{Digest: childDgst, Size: 200}},
	}

	_, err = ms.Put(context.Background(), manifest)
	if err != nil {
		t.Fatal(err)
	}

	if len(store.putManifestRec.ChildDigests) != 1 {
		t.Fatalf("child digests = %d, want 1", len(store.putManifestRec.ChildDigests))
	}
	if store.putManifestRec.ChildDigests[0] != childDgst {
		t.Errorf("child digest = %s, want %s", store.putManifestRec.ChildDigests[0], childDgst)
	}
	if len(store.putManifestRec.BlobDigests) != 0 {
		t.Errorf("blob digests = %d, want 0 (should be classified as children)", len(store.putManifestRec.BlobDigests))
	}
}

func TestManifestPut_StorageFailure_PassesThrough(t *testing.T) {
	store := &mockStore{ensureRepoID: 1}
	storageErr := errors.New("disk full")

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ms:   &mockManifestService{putErr: storageErr},
	}
	repo := newRepository(innerRepo, store, "library")
	ms, _ := repo.Manifests(context.Background())

	_, err := ms.Put(context.Background(), &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{}`),
	})
	if !errors.Is(err, storageErr) {
		t.Errorf("err = %v, want %v", err, storageErr)
	}
}

func TestManifestPut_MetadataFailure_BlocksOperation(t *testing.T) {
	dbErr := errors.New("db locked")
	store := &mockStore{ensureRepoID: 1, putManifestErr: dbErr}

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ms:   &mockManifestService{putDigest: digest.FromString("m")},
	}
	repo := newRepository(innerRepo, store, "library")
	ms, _ := repo.Manifests(context.Background())

	_, err := ms.Put(context.Background(), &mockManifest{
		mediaType: "application/vnd.oci.image.manifest.v1+json",
		payload:   []byte(`{}`),
	})
	if err == nil {
		t.Fatal("expected error when metadata write fails")
	}
	var mwe *MetadataWriteError
	if !errors.As(err, &mwe) {
		t.Errorf("expected MetadataWriteError, got %T", err)
	}
}

func TestManifestDelete_RecordsMetadata(t *testing.T) {
	store := &mockStore{ensureRepoID: 1}
	dgst := digest.FromString("to-delete")

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ms:   &mockManifestService{},
	}
	repo := newRepository(innerRepo, store, "library")
	ms, _ := repo.Manifests(context.Background())

	if err := ms.Delete(context.Background(), dgst); err != nil {
		t.Fatal(err)
	}
	if store.deleteManifestDgst != dgst {
		t.Errorf("deleted digest = %s, want %s", store.deleteManifestDgst, dgst)
	}
	if store.lastRepoID != 1 {
		t.Errorf("repoID = %d, want 1", store.lastRepoID)
	}
}

func TestBlobPut_RecordsMetadata(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putBlobID: 5}
	desc := v1.Descriptor{Digest: digest.FromString("blob"), Size: 42}

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		bs:   &mockBlobStore{putDesc: desc},
	}
	repo := newRepository(innerRepo, store, "library")
	bs := repo.Blobs(context.Background())

	got, err := bs.Put(context.Background(), "application/octet-stream", []byte("data"))
	if err != nil {
		t.Fatal(err)
	}
	if got.Digest != desc.Digest {
		t.Errorf("digest = %s, want %s", got.Digest, desc.Digest)
	}
	if store.putBlobRec.Digest != desc.Digest {
		t.Errorf("stored digest = %s, want %s", store.putBlobRec.Digest, desc.Digest)
	}
}

func TestBlobCommit_RecordsMetadata(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putBlobID: 5}
	desc := v1.Descriptor{Digest: digest.FromString("committed-blob"), Size: 99}
	innerBW := &mockBlobWriter{commitDesc: desc}

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		bs:   &mockBlobStore{createWr: innerBW},
	}
	repo := newRepository(innerRepo, store, "library")
	bs := repo.Blobs(context.Background())

	wr, err := bs.Create(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	got, err := wr.Commit(context.Background(), v1.Descriptor{})
	if err != nil {
		t.Fatal(err)
	}
	if got.Digest != desc.Digest {
		t.Errorf("digest = %s, want %s", got.Digest, desc.Digest)
	}
	if store.putBlobRec.Digest != desc.Digest {
		t.Errorf("stored digest = %s, want %s", store.putBlobRec.Digest, desc.Digest)
	}
}

func TestBlobCreate_MountRecordsMetadata(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putBlobID: 5}
	blobDgst := digest.FromString("mounted-blob")
	desc := v1.Descriptor{Digest: blobDgst, Size: 77}
	fromNamed, _ := reference.WithName("other/repo")
	fromRef, _ := reference.WithDigest(fromNamed, blobDgst)

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		bs: &mockBlobStore{
			createErr: distribution.ErrBlobMounted{From: fromRef, Descriptor: desc},
		},
	}
	repo := newRepository(innerRepo, store, "library")
	bs := repo.Blobs(context.Background())

	_, err := bs.Create(context.Background())
	// ErrBlobMounted is still returned (distribution convention).
	var mounted distribution.ErrBlobMounted
	if !errors.As(err, &mounted) {
		t.Fatalf("expected ErrBlobMounted, got %v", err)
	}
	if store.putBlobRec.Digest != desc.Digest {
		t.Errorf("stored digest = %s, want %s", store.putBlobRec.Digest, desc.Digest)
	}
}

func TestTagService_Get_InvalidDigestAsTag(t *testing.T) {
	store := &mockStore{ensureRepoID: 1}
	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ts:   &mockTagService{},
	}
	repo := newRepository(innerRepo, store, "library")
	ts := repo.Tags(t.Context())

	_, err := ts.Get(t.Context(), "sha256:totallywrong")
	var tagUnknown distribution.ErrTagUnknown
	if !errors.As(err, &tagUnknown) {
		t.Fatalf("expected ErrTagUnknown, got %T: %v", err, err)
	}
	if tagUnknown.Tag != "sha256:totallywrong" {
		t.Errorf("tag = %q, want %q", tagUnknown.Tag, "sha256:totallywrong")
	}
}

func TestTagService_Get_ValidTag(t *testing.T) {
	store := &mockStore{ensureRepoID: 1}
	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ts:   &mockTagService{},
	}
	repo := newRepository(innerRepo, store, "library")
	ts := repo.Tags(t.Context())

	_, err := ts.Get(t.Context(), "latest")
	if err != nil {
		t.Fatalf("unexpected error for valid tag: %v", err)
	}
}

func TestTagService_Tag(t *testing.T) {
	store := &mockStore{ensureRepoID: 1, putTagID: 3}
	desc := v1.Descriptor{Digest: digest.FromString("tagged")}

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ts:   &mockTagService{},
	}
	repo := newRepository(innerRepo, store, "library")
	ts := repo.Tags(context.Background())

	if err := ts.Tag(context.Background(), "v2", desc); err != nil {
		t.Fatal(err)
	}
	if store.putTagRec.Name != "v2" {
		t.Errorf("tag name = %q, want %q", store.putTagRec.Name, "v2")
	}
	if store.putTagRec.Digest != desc.Digest {
		t.Errorf("tag digest = %s, want %s", store.putTagRec.Digest, desc.Digest)
	}
	if store.lastRepoID != 1 {
		t.Errorf("repoID = %d, want 1", store.lastRepoID)
	}
}

func TestTagService_Untag(t *testing.T) {
	store := &mockStore{ensureRepoID: 1}

	innerRepo := &fakeDistRepo{
		name: namedRef(t),
		ts:   &mockTagService{},
	}
	repo := newRepository(innerRepo, store, "library")
	ts := repo.Tags(context.Background())

	if err := ts.Untag(context.Background(), "old"); err != nil {
		t.Fatal(err)
	}
	if store.deleteTagName != "old" {
		t.Errorf("deleted tag = %q, want %q", store.deleteTagName, "old")
	}
	if store.lastRepoID != 1 {
		t.Errorf("repoID = %d, want 1", store.lastRepoID)
	}
}

func namedRef(t *testing.T) reference.Named {
	t.Helper()
	ref, err := reference.WithName("library/test")
	if err != nil {
		t.Fatal(err)
	}
	return ref
}
