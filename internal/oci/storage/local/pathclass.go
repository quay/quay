package local

import (
	"fmt"
	"strings"

	"github.com/opencontainers/go-digest"
)

type pathKind int

const (
	pathBlob pathKind = iota
	pathUpload
	pathMetadata
)

func classify(path string) pathKind {
	if strings.Contains(path, "/_uploads/") {
		return pathUpload
	}
	if strings.Contains(path, "/blobs/") {
		return pathBlob
	}
	return pathMetadata
}

// digestFromBlobPath extracts a digest from a distribution blob path.
// Path format: .../blobs/<algorithm>/<2-hex>/<full-hex>/data
func digestFromBlobPath(path string) (digest.Digest, error) {
	idx := strings.Index(path, "/blobs/")
	if idx < 0 {
		return "", fmt.Errorf("not a blob path: %s", path)
	}
	remainder := path[idx+len("/blobs/"):]
	remainder = strings.TrimSuffix(remainder, "/data")
	// remainder: sha256/aa/aabbccdd
	parts := strings.SplitN(remainder, "/", 3)
	if len(parts) < 3 {
		return "", fmt.Errorf("malformed blob path: %s", path)
	}
	return digest.Parse(parts[0] + ":" + parts[2])
}

// uploadIDFromPath extracts the upload UUID from a distribution upload path.
// Path format: .../_uploads/<uuid>/...
func uploadIDFromPath(path string) string {
	idx := strings.Index(path, "/_uploads/")
	if idx < 0 {
		return ""
	}
	remainder := path[idx+len("/_uploads/"):]
	if slash := strings.IndexByte(remainder, '/'); slash >= 0 {
		return remainder[:slash]
	}
	return remainder
}

// repoFromPath extracts the repository name from a distribution path.
// Path format: .../repositories/<name>/...
func repoFromPath(path string) string {
	const prefix = "/repositories/"
	idx := strings.Index(path, prefix)
	if idx < 0 {
		return ""
	}
	remainder := path[idx+len(prefix):]
	// Find the first distribution-internal segment
	for _, seg := range []string{"/_layers", "/_manifests", "/_uploads"} {
		if i := strings.Index(remainder, seg); i >= 0 {
			return remainder[:i]
		}
	}
	return strings.TrimSuffix(remainder, "/")
}

// uploadRelPath returns the path relative to the uploads/ directory.
// Input: .../repositories/<name>/_uploads/<uuid>/... → <uuid>/...
func uploadRelPath(path string) string {
	idx := strings.Index(path, "/_uploads/")
	if idx < 0 {
		return path
	}
	return path[idx+len("/_uploads/"):]
}
