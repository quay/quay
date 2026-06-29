package local_test

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"testing"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci/storage"
	"github.com/quay/quay/internal/oci/storage/local"
)

func makeDigest(data []byte) digest.Digest {
	return digest.FromBytes(data)
}

func setupDriver(t *testing.T) *local.Driver {
	t.Helper()
	d, err := local.New(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	return d
}

func setupDriverWithRoot(t *testing.T) (d *local.Driver, root string) {
	t.Helper()
	root = t.TempDir()
	var err error
	d, err = local.New(root)
	if err != nil {
		t.Fatal(err)
	}
	return d, root
}

func TestPutGetContent(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	data := []byte("hello world")
	dgst := makeDigest(data)

	if err := d.PutContent(ctx, dgst, data); err != nil {
		t.Fatal(err)
	}

	got, err := d.GetContent(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, data) {
		t.Errorf("got %q, want %q", got, data)
	}
}

func TestPutContentVerifiesDigest(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	data := []byte("real content")
	wrongDigest := makeDigest([]byte("different content"))

	err := d.PutContent(ctx, wrongDigest, data)
	if err == nil {
		t.Fatal("expected error when content doesn't match digest")
	}
}

func TestStatAndDelete(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	data := []byte("stat me")
	dgst := makeDigest(data)

	if err := d.PutContent(ctx, dgst, data); err != nil {
		t.Fatal(err)
	}

	info, err := d.Stat(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size != int64(len(data)) {
		t.Errorf("size = %d, want %d", info.Size, len(data))
	}
	if info.Digest != dgst {
		t.Errorf("digest = %s, want %s", info.Digest, dgst)
	}

	if err := d.Delete(ctx, dgst); err != nil {
		t.Fatal(err)
	}

	_, err = d.Stat(ctx, dgst)
	if !errors.Is(err, storage.ErrNotExist) {
		t.Errorf("stat after delete: got %v, want ErrNotExist", err)
	}
}

func TestGetContentNotExist(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	dgst := makeDigest([]byte("does not exist"))

	_, err := d.GetContent(ctx, dgst)
	if !errors.Is(err, storage.ErrNotExist) {
		t.Errorf("got %v, want ErrNotExist", err)
	}
}

func TestReaderWithOffset(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	data := []byte("abcdefghij")
	dgst := makeDigest(data)

	if err := d.PutContent(ctx, dgst, data); err != nil {
		t.Fatal(err)
	}

	rc, err := d.Reader(ctx, dgst, 5)
	if err != nil {
		t.Fatal(err)
	}
	defer rc.Close()

	got, err := io.ReadAll(rc)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "fghij" {
		t.Errorf("got %q, want %q", got, "fghij")
	}
}

func TestWriter(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	data := []byte("streamed content")
	dgst := makeDigest(data)

	w, err := d.Writer(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.Write(data); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	got, err := d.GetContent(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, data) {
		t.Errorf("got %q, want %q", got, data)
	}
}

func TestConcurrentPutContent(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()
	data := []byte("concurrent write")
	dgst := makeDigest(data)

	errs := make(chan error, 10)
	for i := 0; i < 10; i++ {
		go func() {
			errs <- d.PutContent(ctx, dgst, data)
		}()
	}
	for i := 0; i < 10; i++ {
		if err := <-errs; err != nil {
			t.Errorf("concurrent PutContent: %v", err)
		}
	}

	got, err := d.GetContent(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, data) {
		t.Errorf("content mismatch after concurrent writes")
	}
}

func TestPathCompatibility(t *testing.T) {
	root := t.TempDir()
	d, err := local.New(root)
	if err != nil {
		t.Fatal(err)
	}
	ctx := t.Context()
	data := []byte("path compat test")
	dgst := makeDigest(data)

	if err := d.PutContent(ctx, dgst, data); err != nil {
		t.Fatal(err)
	}

	expectedPath := fmt.Sprintf("%s/sha256/%s/%s", root, dgst.Encoded()[:2], dgst.Encoded())
	got, err := os.ReadFile(expectedPath)
	if err != nil {
		t.Fatalf("file not at expected path: %v", err)
	}
	if !bytes.Equal(got, data) {
		t.Error("content at Python-compatible path doesn't match")
	}
}

func TestPythonPathCompatibility(t *testing.T) {
	// Verify that blobs written by Python at known paths are readable by our driver.
	// This simulates the migration scenario: Python wrote blobs, Go reads them.
	tests := []struct {
		name   string
		digest string
		path   string
	}{
		{
			name:   "empty content sha256",
			digest: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
			path:   "sha256/e3/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
		},
		{
			name:   "leading zeros",
			digest: "sha256:0000000000000000000000000000000000000000000000000000000000000000",
			path:   "sha256/00/0000000000000000000000000000000000000000000000000000000000000000",
		},
		{
			name:   "all f's",
			digest: "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
			path:   "sha256/ff/ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
		},
	}

	root := t.TempDir()
	d, err := local.New(root)
	if err != nil {
		t.Fatal(err)
	}
	ctx := t.Context()

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dgst := digest.Digest(tt.digest)
			data := []byte("content for " + tt.name)

			// Simulate Python writing the blob at the expected path.
			absPath := filepath.Join(root, tt.path)
			if err := os.MkdirAll(filepath.Dir(absPath), 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(absPath, data, 0o644); err != nil {
				t.Fatal(err)
			}

			// Verify our driver can read it at the same digest.
			got, err := d.GetContent(ctx, dgst)
			if err != nil {
				t.Fatalf("GetContent for Python-written blob at %s: %v", tt.path, err)
			}
			if !bytes.Equal(got, data) {
				t.Error("content mismatch reading Python-written blob")
			}
		})
	}
}
