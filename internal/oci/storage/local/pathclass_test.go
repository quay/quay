package local

import (
	"testing"

	"github.com/opencontainers/go-digest"
)

func TestClassify(t *testing.T) {
	tests := []struct {
		path string
		want pathKind
	}{
		{"/docker/registry/v2/blobs/sha256/aa/aabb/data", pathBlob},
		{"/docker/registry/v2/repositories/lib/test/_uploads/uuid-123/data", pathUpload},
		{"/docker/registry/v2/repositories/lib/test/_uploads/uuid-123/startedat", pathUpload},
		{"/docker/registry/v2/repositories/lib/test/_uploads/uuid-123/hashstates/sha256/1024", pathUpload},
		{"/docker/registry/v2/repositories/lib/test/_layers/sha256/aabb/link", pathMetadata},
		{"/docker/registry/v2/repositories/lib/test/_manifests/revisions/sha256/aabb/link", pathMetadata},
		{"/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/current/link", pathMetadata},
		{"/docker/registry/v2/repositories/lib/test/_manifests/tags/latest/index/sha256/aabb/link", pathMetadata},
		{"/docker/registry/v2/repositories/", pathMetadata},
	}
	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			if got := classify(tt.path); got != tt.want {
				t.Errorf("classify(%q) = %d, want %d", tt.path, got, tt.want)
			}
		})
	}
}

func TestDigestFromBlobPath(t *testing.T) {
	path := "/docker/registry/v2/blobs/sha256/aa/aabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccdd/data"
	got, err := digestFromBlobPath(path)
	if err != nil {
		t.Fatal(err)
	}
	want := digest.NewDigestFromEncoded("sha256", "aabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccdd")
	if got != want {
		t.Errorf("digestFromBlobPath = %s, want %s", got, want)
	}
}

func TestUploadIDFromPath(t *testing.T) {
	tests := []struct {
		path string
		want string
	}{
		{"/docker/registry/v2/repositories/lib/test/_uploads/abc-123/data", "abc-123"},
		{"/docker/registry/v2/repositories/lib/test/_uploads/abc-123/startedat", "abc-123"},
		{"/docker/registry/v2/repositories/lib/test/_uploads/abc-123/hashstates/sha256/0", "abc-123"},
	}
	for _, tt := range tests {
		if got := uploadIDFromPath(tt.path); got != tt.want {
			t.Errorf("uploadIDFromPath(%q) = %q, want %q", tt.path, got, tt.want)
		}
	}
}

func TestRepoFromPath(t *testing.T) {
	tests := []struct {
		path string
		want string
	}{
		{"/docker/registry/v2/repositories/lib/test/_layers/sha256/aa/link", "lib/test"},
		{"/docker/registry/v2/repositories/myns/myrepo/_manifests/tags/v1/current/link", "myns/myrepo"},
		{"/docker/registry/v2/repositories/a/b/c/_uploads/uuid/data", "a/b/c"},
	}
	for _, tt := range tests {
		if got := repoFromPath(tt.path); got != tt.want {
			t.Errorf("repoFromPath(%q) = %q, want %q", tt.path, got, tt.want)
		}
	}
}

func TestUploadRelPath(t *testing.T) {
	tests := []struct {
		path string
		want string
	}{
		{"/docker/registry/v2/repositories/lib/test/_uploads/abc/data", "abc/data"},
		{"/docker/registry/v2/repositories/lib/test/_uploads/abc/startedat", "abc/startedat"},
		{"/docker/registry/v2/repositories/lib/test/_uploads/abc/hashstates/sha256/0", "abc/hashstates/sha256/0"},
	}
	for _, tt := range tests {
		if got := uploadRelPath(tt.path); got != tt.want {
			t.Errorf("uploadRelPath(%q) = %q, want %q", tt.path, got, tt.want)
		}
	}
}
