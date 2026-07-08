package local

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"path/filepath"
	"testing"

	"github.com/opencontainers/go-digest"

	storagedriver "github.com/distribution/distribution/v3/registry/storage/driver"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
)

func setupDistTest(t *testing.T) (*DistDriver, oci.BlobStore, oci.MetadataStore) {
	t.Helper()
	rootDir := t.TempDir()
	blobs, err := New(rootDir)
	if err != nil {
		t.Fatal(err)
	}

	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })

	store, err := metastore.NewSQLiteStore(t.Context(), db)
	if err != nil {
		t.Fatal(err)
	}

	dd := NewDistDriver(blobs, store)
	return dd, blobs, store
}

func layerLinkPath(dgst digest.Digest) string {
	return "/docker/registry/v2/repositories/lib/test/_layers/sha256/" + dgst.Encoded() + "/link"
}

func requirePathNotFound(t *testing.T, err error) {
	t.Helper()
	var pnf storagedriver.PathNotFoundError
	if !errors.As(err, &pnf) {
		t.Fatalf("expected PathNotFoundError, got %v", err)
	}
}

func TestDistDriver_Name(t *testing.T) {
	dd, _, _ := setupDistTest(t)
	if dd.Name() != "quay" {
		t.Errorf("Name() = %q, want %q", dd.Name(), "quay")
	}
}

func TestDistDriver_BlobPutGetContent(t *testing.T) {
	dd, blobs, _ := setupDistTest(t)
	ctx := t.Context()

	content := []byte("hello blob")
	dgst := digest.FromBytes(content)
	blobPath := "/docker/registry/v2/blobs/sha256/" + dgst.Encoded()[:2] + "/" + dgst.Encoded() + "/data"

	if err := blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}

	got, err := dd.GetContent(ctx, blobPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, content) {
		t.Errorf("GetContent = %q, want %q", got, content)
	}
}

func TestDistDriver_UploadLifecycle(t *testing.T) {
	dd, blobs, _ := setupDistTest(t)
	ctx := t.Context()

	// Init upload through BlobStore
	uploadID, err := blobs.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}
	dataPath := "/docker/registry/v2/repositories/lib/test/_uploads/" + uploadID + "/data"
	startedAtPath := "/docker/registry/v2/repositories/lib/test/_uploads/" + uploadID + "/startedat"

	// Write startedat via DistDriver (routes through BlobStore.PutUploadState)
	if err := dd.PutContent(ctx, startedAtPath, []byte("2026-06-18T00:00:00Z")); err != nil {
		t.Fatal(err)
	}

	// Read it back
	got, err := dd.GetContent(ctx, startedAtPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "2026-06-18T00:00:00Z" {
		t.Errorf("GetContent(startedat) = %q", got)
	}

	// Write upload data via Writer (routes through BlobStore.UploadWriter)
	w, err := dd.Writer(ctx, dataPath, false)
	if err != nil {
		t.Fatal(err)
	}
	content := []byte("blob content here")
	if _, err := w.Write(content); err != nil {
		t.Fatal(err)
	}
	if err := w.Commit(ctx); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	// Stat the upload data file
	fi, err := dd.Stat(ctx, dataPath)
	if err != nil {
		t.Fatal(err)
	}
	if fi.Size() != int64(len(content)) {
		t.Errorf("Stat size = %d, want %d", fi.Size(), len(content))
	}

	// Delete upload dir
	uploadDir := "/docker/registry/v2/repositories/lib/test/_uploads/" + uploadID
	if err := dd.Delete(ctx, uploadDir); err != nil {
		t.Fatal(err)
	}
	_, err = dd.Stat(ctx, dataPath)
	requirePathNotFound(t, err)
}

func TestDistDriver_Move_UploadToBlob(t *testing.T) {
	dd, blobs, _ := setupDistTest(t)
	ctx := t.Context()

	content := []byte("finalized blob")
	dgst := digest.FromBytes(content)

	// Init upload and write data through BlobStore
	uploadID, err := blobs.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}
	w, err := blobs.UploadWriter(ctx, uploadID, false)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.Write(content); err != nil {
		t.Fatal(err)
	}
	if err := w.Commit(ctx); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	// Move to blob path via DistDriver
	uploadDataPath := "/docker/registry/v2/repositories/lib/test/_uploads/" + uploadID + "/data"
	blobPath := "/docker/registry/v2/blobs/sha256/" + dgst.Encoded()[:2] + "/" + dgst.Encoded() + "/data"
	if err := dd.Move(ctx, uploadDataPath, blobPath); err != nil {
		t.Fatal(err)
	}

	// Verify blob is accessible via BlobStore
	got, err := blobs.GetContent(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, content) {
		t.Errorf("blob content = %q, want %q", got, content)
	}
}

func TestDistDriver_MetadataLink_GetContent(t *testing.T) {
	dd, _, store := setupDistTest(t)
	ctx := t.Context()

	repoID, _ := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "lib", Name: "test"})
	manifestDgst := digest.FromString("my-manifest")
	layerDgst := digest.FromString("my-layer")
	store.PutBlob(ctx, oci.BlobRecord{Digest: layerDgst, Size: 100})
	store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:      manifestDgst,
		MediaType:   "application/vnd.oci.image.manifest.v1+json",
		Content:     []byte(`{}`),
		BlobDigests: []oci.BlobRef{{Digest: layerDgst, Size: 100}},
		Tag:         "latest",
	})

	// Read tag current link
	tagPath := "/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/current/link"
	got, err := dd.GetContent(ctx, tagPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != manifestDgst.String() {
		t.Errorf("tag link = %q, want %q", got, manifestDgst.String())
	}

	// Read layer link (repo-scoped via manifestblob)
	layerPath := layerLinkPath(layerDgst)
	got, err = dd.GetContent(ctx, layerPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != layerDgst.String() {
		t.Errorf("layer link = %q, want %q", got, layerDgst.String())
	}
}

func TestDistDriver_LayerLinkRequiresRepoAssociation(t *testing.T) {
	dd, _, store := setupDistTest(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "lib", Name: "test"})
	if err != nil {
		t.Fatal(err)
	}
	layerDgst := digest.FromString("global-only-layer")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: layerDgst, Size: 100}); err != nil {
		t.Fatal(err)
	}

	_, err = dd.GetContent(ctx, layerLinkPath(layerDgst))
	requirePathNotFound(t, err)

	linked, err := store.BlobLinkedToRepo(ctx, repoID, layerDgst)
	if err != nil {
		t.Fatal(err)
	}
	if linked {
		t.Fatal("BlobLinkedToRepo = true for global-only blob")
	}
}

func TestDistDriver_DeleteLayerLinkRemovesUploadedAssociation(t *testing.T) {
	dd, _, store := setupDistTest(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "lib", Name: "test"})
	if err != nil {
		t.Fatal(err)
	}
	layerDgst := digest.FromString("uploaded-layer")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: layerDgst, Size: 100}); err != nil {
		t.Fatal(err)
	}
	if err := store.PutUploadedBlob(ctx, repoID, layerDgst); err != nil {
		t.Fatal(err)
	}

	layerPath := layerLinkPath(layerDgst)
	got, err := dd.GetContent(ctx, layerPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != layerDgst.String() {
		t.Errorf("layer link = %q, want %q", got, layerDgst.String())
	}

	if err := dd.Delete(ctx, layerPath); err != nil {
		t.Fatal(err)
	}
	_, err = dd.GetContent(ctx, layerPath)
	requirePathNotFound(t, err)

	exists, err := store.BlobExists(ctx, layerDgst)
	if err != nil {
		t.Fatal(err)
	}
	if !exists {
		t.Fatal("BlobExists = false after deleting repo-scoped layer link")
	}
}

func TestDistDriver_DeleteLayerLinkKeepsManifestAssociation(t *testing.T) {
	dd, _, store := setupDistTest(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "lib", Name: "test"})
	if err != nil {
		t.Fatal(err)
	}
	layerDgst := digest.FromString("manifest-layer")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: layerDgst, Size: 100}); err != nil {
		t.Fatal(err)
	}
	if err := store.PutUploadedBlob(ctx, repoID, layerDgst); err != nil {
		t.Fatal(err)
	}
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:      digest.FromString("manifest-for-layer-delete"),
		MediaType:   "application/vnd.oci.image.manifest.v1+json",
		Content:     []byte(`{}`),
		BlobDigests: []oci.BlobRef{{Digest: layerDgst, Size: 100}},
		Tag:         "latest",
	}); err != nil {
		t.Fatal(err)
	}

	layerPath := layerLinkPath(layerDgst)
	if err := dd.Delete(ctx, layerPath); err != nil {
		t.Fatal(err)
	}

	got, err := dd.GetContent(ctx, layerPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != layerDgst.String() {
		t.Errorf("layer link after delete = %q, want %q", got, layerDgst.String())
	}
}

func TestDistDriver_MetadataLink_PutContent_NoOp(t *testing.T) {
	dd, _, _ := setupDistTest(t)
	ctx := t.Context()

	linkPath := "/docker/registry/v2/repositories/lib/test/_layers/sha256/aabb/link"
	if err := dd.PutContent(ctx, linkPath, []byte("sha256:aabb")); err != nil {
		t.Fatalf("PutContent on link should be no-op, got error: %v", err)
	}
}

func TestDistDriver_ManifestBlobFallbackFromMetadata(t *testing.T) {
	dd, _, store := setupDistTest(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "lib", Name: "test"})
	if err != nil {
		t.Fatal(err)
	}
	manifestContent := []byte(`{"schemaVersion":2}`)
	manifestDgst := digest.FromBytes(manifestContent)
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    manifestDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   manifestContent,
		Tag:       "latest",
	}); err != nil {
		t.Fatal(err)
	}

	blobPath := "/docker/registry/v2/blobs/sha256/" + manifestDgst.Encoded()[:2] + "/" + manifestDgst.Encoded() + "/data"

	got, err := dd.GetContent(ctx, blobPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, manifestContent) {
		t.Errorf("GetContent = %s, want %s", got, manifestContent)
	}

	rc, err := dd.Reader(ctx, blobPath, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = rc.Close() }()
	read, err := io.ReadAll(rc)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(read, manifestContent) {
		t.Errorf("Reader = %s, want %s", read, manifestContent)
	}

	info, err := dd.Stat(ctx, blobPath)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size() != int64(len(manifestContent)) {
		t.Errorf("Stat size = %d, want %d", info.Size(), len(manifestContent))
	}
}

func TestDistDriver_ListTags(t *testing.T) {
	dd, _, store := setupDistTest(t)
	ctx := t.Context()

	repoID, _ := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "lib", Name: "test"})
	d1 := digest.FromString("m1")
	store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: d1, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "v1",
	})

	tagsDir := "/docker/registry/v2/repositories/lib/test/_manifests/tags"
	tags, err := dd.List(ctx, tagsDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(tags) != 1 || tags[0] != tagsDir+"/v1" {
		t.Errorf("List(tags) = %v, want [%s/v1]", tags, tagsDir)
	}
}

func TestDistDriver_RedirectURL(t *testing.T) {
	dd, _, _ := setupDistTest(t)
	url, err := dd.RedirectURL(nil, "/any/path")
	if err != nil {
		t.Fatal(err)
	}
	if url != "" {
		t.Errorf("RedirectURL = %q, want empty", url)
	}
}

// errStubMetaStore is a minimal MetadataStore mock that returns a configurable
// error from GetRepositoryID. All other methods return errNotImplemented.
type errStubMetaStore struct {
	getRepoErr error
}

var errNotImplemented = errors.New("not implemented")

func (s *errStubMetaStore) EnsureRepository(context.Context, oci.RepositoryName) (int64, error) {
	return 0, errNotImplemented
}
func (s *errStubMetaStore) PutManifest(context.Context, int64, oci.ManifestRecord) (int64, error) {
	return 0, errNotImplemented
}
func (s *errStubMetaStore) DeleteManifest(context.Context, int64, digest.Digest) error {
	return errNotImplemented
}
func (s *errStubMetaStore) PutBlob(context.Context, oci.BlobRecord) (int64, error) {
	return 0, errNotImplemented
}
func (s *errStubMetaStore) PutTag(context.Context, int64, oci.TagRecord) (int64, error) {
	return 0, errNotImplemented
}
func (s *errStubMetaStore) DeleteTag(context.Context, int64, string) error { return errNotImplemented }
func (s *errStubMetaStore) GetRepositoryID(_ context.Context, _ oci.RepositoryName) (int64, error) {
	return 0, s.getRepoErr
}
func (s *errStubMetaStore) GetTagDigest(context.Context, int64, string) (digest.Digest, error) {
	return "", errNotImplemented
}
func (s *errStubMetaStore) GetManifestDigest(context.Context, int64, digest.Digest) (digest.Digest, error) {
	return "", errNotImplemented
}
func (s *errStubMetaStore) GetManifestContent(context.Context, digest.Digest) ([]byte, error) {
	return nil, errNotImplemented
}
func (s *errStubMetaStore) BlobExists(context.Context, digest.Digest) (bool, error) {
	return false, errNotImplemented
}
func (s *errStubMetaStore) BlobLinkedToRepo(context.Context, int64, digest.Digest) (bool, error) {
	return false, errNotImplemented
}
func (s *errStubMetaStore) ListTags(context.Context, int64) ([]string, error) {
	return nil, errNotImplemented
}
func (s *errStubMetaStore) ListRepositories(context.Context) ([]oci.RepositoryName, error) {
	return nil, errNotImplemented
}
func (s *errStubMetaStore) PutUploadedBlob(context.Context, int64, digest.Digest) error {
	return errNotImplemented
}
func (s *errStubMetaStore) DeleteUploadedBlob(context.Context, int64, digest.Digest) (int64, error) {
	return 0, errNotImplemented
}
func (s *errStubMetaStore) CleanExpiredUploadedBlobs(context.Context) error { return errNotImplemented }

func TestDistDriver_GetRepositoryID_PropagatesNonNotExistError(t *testing.T) {
	dbErr := errors.New("database connection timeout")
	stub := &errStubMetaStore{getRepoErr: dbErr}
	dd := NewDistDriver(nil, stub)
	ctx := t.Context()

	t.Run("getMetadataContent", func(t *testing.T) {
		tagPath := "/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/current/link"
		_, err := dd.GetContent(ctx, tagPath)
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		var pnf storagedriver.PathNotFoundError
		if errors.As(err, &pnf) {
			t.Fatalf("non-ErrNotExist error was converted to PathNotFoundError: %v", err)
		}
		if !errors.Is(err, dbErr) {
			t.Fatalf("expected original error %q, got %q", dbErr, err)
		}
	})

	t.Run("listTags", func(t *testing.T) {
		tagsDir := "/docker/registry/v2/repositories/lib/test/_manifests/tags"
		_, err := dd.List(ctx, tagsDir)
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		var pnf storagedriver.PathNotFoundError
		if errors.As(err, &pnf) {
			t.Fatalf("non-ErrNotExist error was converted to PathNotFoundError: %v", err)
		}
		if !errors.Is(err, dbErr) {
			t.Fatalf("expected original error %q, got %q", dbErr, err)
		}
	})

	t.Run("deleteLayerLink", func(t *testing.T) {
		layerPath := "/docker/registry/v2/repositories/lib/test/_layers/sha256/aabbccdd/link"
		err := dd.Delete(ctx, layerPath)
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		var pnf storagedriver.PathNotFoundError
		if errors.As(err, &pnf) {
			t.Fatalf("non-ErrNotExist error was converted to PathNotFoundError: %v", err)
		}
		if !errors.Is(err, dbErr) {
			t.Fatalf("expected original error %q, got %q", dbErr, err)
		}
	})

	t.Run("statMetadata", func(t *testing.T) {
		tagPath := "/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/current/link"
		_, err := dd.Stat(ctx, tagPath)
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		var pnf storagedriver.PathNotFoundError
		if errors.As(err, &pnf) {
			t.Fatalf("non-ErrNotExist error was converted to PathNotFoundError: %v", err)
		}
		if !errors.Is(err, dbErr) {
			t.Fatalf("expected original error %q, got %q", dbErr, err)
		}
	})
}

func TestDistDriver_GetRepositoryID_ErrNotExist_ReturnsPathNotFound(t *testing.T) {
	notExistErr := fmt.Errorf("get repository lib/test: %w", oci.ErrNotExist)
	stub := &errStubMetaStore{getRepoErr: notExistErr}
	dd := NewDistDriver(nil, stub)
	ctx := t.Context()

	t.Run("getMetadataContent", func(t *testing.T) {
		tagPath := "/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/current/link"
		_, err := dd.GetContent(ctx, tagPath)
		requirePathNotFound(t, err)
	})

	t.Run("listTags", func(t *testing.T) {
		tagsDir := "/docker/registry/v2/repositories/lib/test/_manifests/tags"
		_, err := dd.List(ctx, tagsDir)
		requirePathNotFound(t, err)
	})

	t.Run("deleteLayerLink", func(t *testing.T) {
		layerPath := "/docker/registry/v2/repositories/lib/test/_layers/sha256/aabbccdd/link"
		err := dd.Delete(ctx, layerPath)
		requirePathNotFound(t, err)
	})

	t.Run("statMetadata", func(t *testing.T) {
		tagPath := "/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/current/link"
		_, err := dd.Stat(ctx, tagPath)
		requirePathNotFound(t, err)
	})
}
