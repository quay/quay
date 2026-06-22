package local

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"

	"github.com/google/uuid"
	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage"
)

var uuidRegexp = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

// InitUpload creates a new upload directory and returns its UUID.
func (d *Driver) InitUpload(ctx context.Context) (string, error) {
	id := uuid.New().String()
	dir := d.uploadDir(id)
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return "", err
	}
	f, err := os.Create(filepath.Join(dir, "data")) //nolint:gosec // path from validated UUID
	if err != nil {
		return "", err
	}
	return id, f.Close()
}

func (d *Driver) uploadDir(id string) string {
	return d.absPath(filepath.Join("uploads", id))
}

func (d *Driver) uploadDataPath(id string) string {
	return filepath.Join(d.uploadDir(id), "data")
}

func (d *Driver) validateUploadID(id string) error {
	if !uuidRegexp.MatchString(id) {
		return fmt.Errorf("invalid upload ID %q", id)
	}
	return nil
}

// UploadWriter returns a writer for the upload data file.
func (d *Driver) UploadWriter(ctx context.Context, uploadID string, appendMode bool) (oci.UploadWriter, error) {
	if err := d.validateUploadID(uploadID); err != nil {
		return nil, err
	}

	p := d.uploadDataPath(uploadID)
	if err := os.MkdirAll(filepath.Dir(p), 0o750); err != nil {
		return nil, err
	}

	fp, err := os.OpenFile(p, os.O_WRONLY|os.O_CREATE, 0o600) //nolint:gosec // path from validated UUID
	if err != nil {
		return nil, err
	}

	var offset int64
	if !appendMode {
		if err := fp.Truncate(0); err != nil {
			_ = fp.Close()
			return nil, err
		}
	} else {
		n, err := fp.Seek(0, io.SeekEnd)
		if err != nil {
			_ = fp.Close()
			return nil, err
		}
		offset = n
	}

	return &fileWriter{f: fp, dst: p, size: offset}, nil
}

// UploadReader returns a reader for the upload data file at the given offset.
func (d *Driver) UploadReader(ctx context.Context, uploadID string, offset int64) (io.ReadCloser, error) {
	if err := d.validateUploadID(uploadID); err != nil {
		return nil, err
	}

	f, err := os.Open(d.uploadDataPath(uploadID))
	if os.IsNotExist(err) {
		return nil, storage.ErrNotExist
	}
	if err != nil {
		return nil, err
	}
	if offset > 0 {
		if _, err := f.Seek(offset, io.SeekStart); err != nil {
			_ = f.Close()
			return nil, err
		}
	}
	return f, nil
}

// UploadStat returns size info for the upload data file.
func (d *Driver) UploadStat(ctx context.Context, uploadID string) (oci.BlobInfo, error) {
	if err := d.validateUploadID(uploadID); err != nil {
		return oci.BlobInfo{}, err
	}

	fi, err := os.Stat(d.uploadDataPath(uploadID))
	if os.IsNotExist(err) {
		return oci.BlobInfo{}, storage.ErrNotExist
	}
	if err != nil {
		return oci.BlobInfo{}, err
	}
	return oci.BlobInfo{Size: fi.Size()}, nil
}

// CommitUpload verifies the digest and moves the upload data to content-addressable storage.
func (d *Driver) CommitUpload(ctx context.Context, uploadID string, dgst digest.Digest) error {
	if err := d.validateUploadID(uploadID); err != nil {
		return err
	}

	src := d.uploadDataPath(uploadID)

	f, err := os.Open(src) //nolint:gosec // path from validated UUID
	if err != nil {
		return fmt.Errorf("open upload data: %w", err)
	}
	computed, err := digest.SHA256.FromReader(f)
	_ = f.Close()
	if err != nil {
		return fmt.Errorf("compute digest: %w", err)
	}
	if computed != dgst {
		_ = os.RemoveAll(d.uploadDir(uploadID))
		return fmt.Errorf("digest mismatch: computed %s, expected %s", computed, dgst)
	}

	dst := d.blobPath(dgst)
	if err := os.MkdirAll(filepath.Dir(dst), 0o750); err != nil {
		return err
	}

	if _, err := os.Stat(dst); err == nil {
		_ = os.Remove(src)
	} else {
		if err := os.Rename(src, dst); err != nil {
			return err
		}
	}

	return os.RemoveAll(d.uploadDir(uploadID))
}

// CancelUpload removes the entire upload directory.
func (d *Driver) CancelUpload(ctx context.Context, uploadID string) error {
	if err := d.validateUploadID(uploadID); err != nil {
		return err
	}

	dir := d.uploadDir(uploadID)
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		return fmt.Errorf("upload %s: %w", uploadID, storage.ErrNotExist)
	}
	return os.RemoveAll(dir)
}

// PutUploadState stores metadata for an upload keyed by a relative path
// (e.g., "startedat", "hashstates/sha256/1024").
func (d *Driver) PutUploadState(ctx context.Context, uploadID, key string, data []byte) error {
	if err := d.validateUploadID(uploadID); err != nil {
		return err
	}

	p := filepath.Join(d.uploadDir(uploadID), filepath.FromSlash(key))
	p = filepath.Clean(p)
	base := d.uploadDir(uploadID)
	if !strings.HasPrefix(p, base) {
		return fmt.Errorf("invalid upload state key %q", key)
	}

	if err := os.MkdirAll(filepath.Dir(p), 0o750); err != nil {
		return err
	}
	return os.WriteFile(p, data, 0o600)
}

// GetUploadState retrieves upload metadata by key.
func (d *Driver) GetUploadState(ctx context.Context, uploadID, key string) ([]byte, error) {
	if err := d.validateUploadID(uploadID); err != nil {
		return nil, err
	}

	p := filepath.Join(d.uploadDir(uploadID), filepath.FromSlash(key))
	data, err := os.ReadFile(p) //nolint:gosec // path from validated UUID + key
	if os.IsNotExist(err) {
		return nil, storage.ErrNotExist
	}
	return data, err
}

// ListUploadState lists state keys under a prefix within an upload directory.
func (d *Driver) ListUploadState(ctx context.Context, uploadID, keyPrefix string) ([]string, error) {
	if err := d.validateUploadID(uploadID); err != nil {
		return nil, err
	}

	dir := filepath.Join(d.uploadDir(uploadID), filepath.FromSlash(keyPrefix))
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	result := make([]string, 0, len(entries))
	for _, e := range entries {
		if !e.IsDir() {
			result = append(result, e.Name())
		}
	}
	sort.Strings(result)
	return result, nil
}

// fileWriter implements oci.UploadWriter backed by a local file.
type fileWriter struct {
	mu        sync.Mutex
	f         *os.File
	size      int64
	dst       string
	closed    bool
	committed bool
}

func (w *fileWriter) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.closed {
		return 0, fmt.Errorf("already closed")
	}
	if w.committed {
		return 0, fmt.Errorf("already committed")
	}
	n, err := w.f.Write(p)
	w.size += int64(n)
	return n, err
}

func (w *fileWriter) Size() int64 {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.size
}

func (w *fileWriter) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.closed {
		return nil
	}
	w.closed = true
	return w.f.Close()
}

func (w *fileWriter) Commit(ctx context.Context) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.closed {
		return fmt.Errorf("already closed")
	}
	if w.committed {
		return fmt.Errorf("already committed")
	}
	w.committed = true
	return w.f.Sync()
}

func (w *fileWriter) Cancel(ctx context.Context) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.closed {
		return fmt.Errorf("already closed")
	}
	w.closed = true
	_ = w.f.Close()
	return os.Remove(w.dst)
}
