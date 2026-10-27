package local_test

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/quay/quay/internal/oci/storage/local"
)

func TestUploadWriterHappyPath(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()

	chunk1 := []byte("hello ")
	chunk2 := []byte("world")
	var full []byte
	full = append(full, chunk1...)
	full = append(full, chunk2...)
	dgst := makeDigest(full)

	uploadID, err := d.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}

	// Write first chunk
	w, err := d.UploadWriter(ctx, uploadID, false)
	if err != nil {
		t.Fatal(err)
	}
	n, err := w.Write(chunk1)
	if err != nil {
		t.Fatal(err)
	}
	if n != len(chunk1) {
		t.Errorf("wrote %d, want %d", n, len(chunk1))
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	// Write second chunk (append mode)
	w, err = d.UploadWriter(ctx, uploadID, true)
	if err != nil {
		t.Fatal(err)
	}
	n, err = w.Write(chunk2)
	if err != nil {
		t.Fatal(err)
	}
	if n != len(chunk2) {
		t.Errorf("wrote %d, want %d", n, len(chunk2))
	}
	if err := w.Commit(ctx); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	// Commit the upload
	if err := d.CommitUpload(ctx, uploadID, dgst); err != nil {
		t.Fatal(err)
	}

	got, err := d.GetContent(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, full) {
		t.Errorf("got %q, want %q", got, full)
	}
}

func TestUploadReaderAndStat(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()

	uploadID, err := d.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer d.CancelUpload(ctx, uploadID) //nolint:errcheck // test cleanup

	data := []byte("readable data")
	w, err := d.UploadWriter(ctx, uploadID, false)
	if err != nil {
		t.Fatal(err)
	}
	w.Write(data)
	w.Commit(ctx)
	w.Close()

	// Read back
	rc, err := d.UploadReader(ctx, uploadID, 0)
	if err != nil {
		t.Fatal(err)
	}
	buf := make([]byte, 100)
	n, _ := rc.Read(buf)
	rc.Close()
	if !bytes.Equal(buf[:n], data) {
		t.Errorf("read %q, want %q", buf[:n], data)
	}

	// Stat
	info, err := d.UploadStat(ctx, uploadID)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size != int64(len(data)) {
		t.Errorf("stat size = %d, want %d", info.Size, len(data))
	}
}

func TestUploadState(t *testing.T) {
	d := setupDriver(t)
	ctx := t.Context()

	uploadID, err := d.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer d.CancelUpload(ctx, uploadID) //nolint:errcheck // test cleanup

	// Put/Get simple key
	if err := d.PutUploadState(ctx, uploadID, "startedat", []byte("2026-06-18")); err != nil {
		t.Fatal(err)
	}
	got, err := d.GetUploadState(ctx, uploadID, "startedat")
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "2026-06-18" {
		t.Errorf("got %q, want %q", got, "2026-06-18")
	}

	// Put/Get nested key
	if err := d.PutUploadState(ctx, uploadID, "hashstates/sha256/1024", []byte{0x01, 0x02}); err != nil {
		t.Fatal(err)
	}
	got, err = d.GetUploadState(ctx, uploadID, "hashstates/sha256/1024")
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, []byte{0x01, 0x02}) {
		t.Errorf("hashstate content mismatch")
	}

	// List
	keys, err := d.ListUploadState(ctx, uploadID, "hashstates/sha256")
	if err != nil {
		t.Fatal(err)
	}
	if len(keys) != 1 {
		t.Fatalf("expected 1 key, got %d", len(keys))
	}
	if keys[0] != "1024" {
		t.Errorf("key = %q, want %q", keys[0], "1024")
	}
}

func TestUploadCancel(t *testing.T) {
	d, root := setupDriverWithRoot(t)
	ctx := t.Context()

	uploadID, err := d.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}

	// Write some state
	d.PutUploadState(ctx, uploadID, "startedat", []byte("now"))

	if err := d.CancelUpload(ctx, uploadID); err != nil {
		t.Fatal(err)
	}

	uploadDir := filepath.Join(root, "uploads", uploadID)
	if _, err := os.Stat(uploadDir); !os.IsNotExist(err) {
		t.Errorf("upload dir should be gone after cancel, got err: %v", err)
	}
}

func TestUploadDirLayout(t *testing.T) {
	_, root := setupDriverWithRoot(t)
	d, err := local.New(root)
	if err != nil {
		t.Fatal(err)
	}
	ctx := t.Context()

	uploadID, err := d.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer d.CancelUpload(ctx, uploadID) //nolint:errcheck // test cleanup

	// Upload is now a directory (not flat file)
	uploadDir := filepath.Join(root, "uploads", uploadID)
	fi, err := os.Stat(uploadDir)
	if err != nil {
		t.Fatalf("stat upload dir: %v", err)
	}
	if !fi.IsDir() {
		t.Error("upload path should be a directory")
	}

	// Data file exists inside
	dataPath := filepath.Join(uploadDir, "data")
	if _, err := os.Stat(dataPath); err != nil {
		t.Errorf("data file should exist: %v", err)
	}
}
