// Package local implements oci.BlobStore using the local filesystem.
package local

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage"
)

var _ oci.BlobStore = (*Driver)(nil)

// Driver implements oci.BlobStore using the local filesystem.
// All blob writes are atomic (temp file + rename). All production
// digests are SHA-256; this assumption is documented in the spec.
type Driver struct {
	rootDir string
}

// New creates a local filesystem storage driver rooted at rootDir.
func New(rootDir string) (*Driver, error) {
	if err := os.MkdirAll(rootDir, 0o750); err != nil {
		return nil, err
	}
	return &Driver{rootDir: rootDir}, nil
}

// RootDir returns the storage root directory.
func (d *Driver) RootDir() string { return d.rootDir }

func (d *Driver) absPath(rel string) string {
	return filepath.Join(d.rootDir, filepath.FromSlash(rel))
}

func (d *Driver) blobPath(dgst digest.Digest) string {
	return d.absPath(storage.ContentPath(dgst))
}

// GetContent reads a blob by digest.
func (d *Driver) GetContent(ctx context.Context, dgst digest.Digest) ([]byte, error) {
	data, err := os.ReadFile(d.blobPath(dgst))
	if errors.Is(err, os.ErrNotExist) {
		return nil, storage.ErrNotExist
	}
	return data, err
}

// PutContent atomically writes a blob, verifying the digest matches.
func (d *Driver) PutContent(ctx context.Context, dgst digest.Digest, content []byte) error {
	if digest.FromBytes(content) != dgst {
		return fmt.Errorf("content digest mismatch: got %s, want %s", digest.FromBytes(content), dgst)
	}

	p := d.blobPath(dgst)
	if err := os.MkdirAll(filepath.Dir(p), 0o750); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(p), ".blob-*")
	if err != nil {
		return err
	}
	if _, err := tmp.Write(content); err != nil {
		_ = tmp.Close()
		_ = os.Remove(tmp.Name())
		return err
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmp.Name())
		return err
	}
	if err := os.Rename(tmp.Name(), p); err != nil {
		_ = os.Remove(tmp.Name())
		return err
	}
	return nil
}

// Reader returns a ReadCloser for a blob starting at the given offset.
func (d *Driver) Reader(ctx context.Context, dgst digest.Digest, offset int64) (io.ReadCloser, error) {
	f, err := os.Open(d.blobPath(dgst))
	if errors.Is(err, os.ErrNotExist) {
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

// Writer returns an atomic writer that verifies digest on Close.
func (d *Driver) Writer(ctx context.Context, dgst digest.Digest) (io.WriteCloser, error) {
	p := d.blobPath(dgst)
	if err := os.MkdirAll(filepath.Dir(p), 0o750); err != nil {
		return nil, err
	}
	tmp, err := os.CreateTemp(filepath.Dir(p), ".blob-*")
	if err != nil {
		return nil, err
	}
	return &atomicWriter{tmp: tmp, dst: p, dgst: dgst, hash: digest.SHA256.Digester()}, nil
}

// Stat returns size and digest metadata for a blob.
func (d *Driver) Stat(ctx context.Context, dgst digest.Digest) (oci.BlobInfo, error) {
	fi, err := os.Stat(d.blobPath(dgst))
	if errors.Is(err, os.ErrNotExist) {
		return oci.BlobInfo{}, storage.ErrNotExist
	}
	if err != nil {
		return oci.BlobInfo{}, err
	}
	return oci.BlobInfo{Digest: dgst, Size: fi.Size()}, nil
}

// Delete removes a blob by digest.
func (d *Driver) Delete(ctx context.Context, dgst digest.Digest) error {
	err := os.Remove(d.blobPath(dgst))
	if errors.Is(err, os.ErrNotExist) {
		return storage.ErrNotExist
	}
	return err
}

// atomicWriter writes to a temp file, verifies digest, renames on Close.
type atomicWriter struct {
	tmp  *os.File
	dst  string
	dgst digest.Digest
	hash digest.Digester
}

func (w *atomicWriter) Write(p []byte) (int, error) {
	n, err := w.tmp.Write(p)
	if n > 0 {
		_, _ = w.hash.Hash().Write(p[:n])
	}
	return n, err
}

func (w *atomicWriter) Close() error {
	if err := w.tmp.Close(); err != nil {
		_ = os.Remove(w.tmp.Name())
		return err
	}
	if w.hash.Digest() != w.dgst {
		_ = os.Remove(w.tmp.Name())
		return fmt.Errorf("writer digest mismatch: got %s, want %s", w.hash.Digest(), w.dgst)
	}
	if err := os.Rename(w.tmp.Name(), w.dst); err != nil {
		_ = os.Remove(w.tmp.Name())
		return err
	}
	return nil
}
