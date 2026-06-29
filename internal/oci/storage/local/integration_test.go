package local

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage"
)

func TestIntegration_BlobRoundTrip(t *testing.T) {
	dd, blobs, store := setupDistTest(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "test", Name: "repo"})
	if err != nil {
		t.Fatal(err)
	}

	// Simulate distribution's upload flow
	content := []byte("integration test blob content")
	dgst := digest.FromBytes(content)

	// 1. Init upload through BlobStore
	uploadID, err := blobs.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}
	uploadPrefix := "/docker/registry/v2/repositories/test/repo/_uploads/" + uploadID

	// 2. Write startedat (routes through BlobStore.PutUploadState)
	if err := dd.PutContent(ctx, uploadPrefix+"/startedat", []byte("2026-06-18T00:00:00Z")); err != nil {
		t.Fatal(err)
	}

	// 3. Write upload data via Writer (routes through BlobStore.UploadWriter)
	w, err := dd.Writer(ctx, uploadPrefix+"/data", false)
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

	// 4. Move upload to blob (routes through BlobStore.UploadReader → BlobStore.Writer)
	blobPath := "/docker/registry/v2/blobs/sha256/" + dgst.Encoded()[:2] + "/" + dgst.Encoded() + "/data"
	if err := dd.Move(ctx, uploadPrefix+"/data", blobPath); err != nil {
		t.Fatal(err)
	}

	// 5. Record blob metadata (simulating middleware)
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: int64(len(content))}); err != nil {
		t.Fatal(err)
	}

	// 6. Record manifest (simulating middleware)
	manifestDgst := digest.FromString("manifest-content")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:      manifestDgst,
		MediaType:   "application/vnd.oci.image.manifest.v1+json",
		Content:     []byte(`{"schemaVersion":2}`),
		BlobDigests: []oci.BlobRef{{Digest: dgst, Size: int64(len(content))}},
		Tag:         "latest",
	}); err != nil {
		t.Fatal(err)
	}

	// --- Pull side ---

	// Resolve tag → manifest digest
	tagLink := "/docker/registry/v2/repositories/test/repo/_manifests/tags/latest/current/link"
	tagContent, err := dd.GetContent(ctx, tagLink)
	if err != nil {
		t.Fatal(err)
	}
	if string(tagContent) != manifestDgst.String() {
		t.Errorf("tag resolved to %q, want %q", tagContent, manifestDgst)
	}

	// Resolve manifest revision link
	revLink := "/docker/registry/v2/repositories/test/repo/_manifests/revisions/" +
		manifestDgst.Algorithm().String() + "/" + manifestDgst.Encoded() + "/link"
	revContent, err := dd.GetContent(ctx, revLink)
	if err != nil {
		t.Fatal(err)
	}
	if string(revContent) != manifestDgst.String() {
		t.Errorf("revision link = %q, want %q", revContent, manifestDgst)
	}

	// Read blob content
	blobContent, err := dd.GetContent(ctx, blobPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(blobContent, content) {
		t.Errorf("blob content = %q, want %q", blobContent, content)
	}

	// Verify blob is at Quay's path layout
	localBlobs := blobs.(*Driver)
	quayPath := filepath.Join(localBlobs.RootDir(), storage.ContentPath(dgst))
	if _, err := os.Stat(quayPath); err != nil {
		t.Errorf("blob not at Quay layout path %s: %v", quayPath, err)
	}
}
