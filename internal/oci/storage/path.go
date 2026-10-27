// Package storage defines the content-addressable blob storage interface.
package storage

import (
	"fmt"
	"path"
	"strings"

	"github.com/opencontainers/go-digest"
)

// ContentPath returns the storage-relative path for a content-addressable blob.
// Byte-for-byte identical to Python's digest_tools.content_path().
func ContentPath(dgst digest.Digest) string {
	alg := dgst.Algorithm().String()
	hex := dgst.Encoded()

	normalized := strings.NewReplacer("+", "/", ".", "/").Replace(alg)
	normalized = path.Clean(normalized)

	prefix := hex
	if len(prefix) >= 2 {
		prefix = prefix[:2]
	} else {
		prefix = strings.Repeat("0", 2-len(prefix)) + prefix
	}

	return path.Join(normalized, prefix, hex)
}

// UploadPath returns the scratch path for a chunked upload.
// Matches Python's LocalStorage._rel_upload_path(): uploads/{uploadID} (flat file).
func UploadPath(uploadID string) string {
	return path.Join("uploads", uploadID)
}

// DigestFromPath reverses ContentPath — extracts a digest from a storage path.
// Expects format: {algorithm}/{prefix}/{hex} (exactly 3 segments for simple algorithms).
func DigestFromPath(p string) (digest.Digest, error) {
	parts := strings.Split(p, "/")
	if len(parts) < 3 {
		return "", fmt.Errorf("path %q: too few segments", p)
	}

	hex := parts[len(parts)-1]
	alg := strings.Join(parts[:len(parts)-2], "/")

	if alg == "" || hex == "" {
		return "", fmt.Errorf("path %q: empty algorithm or hex", p)
	}

	return digest.Parse(alg + ":" + hex)
}
