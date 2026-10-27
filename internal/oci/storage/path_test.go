package storage_test

import (
	"testing"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci/storage"
)

func TestContentPath(t *testing.T) {
	tests := []struct {
		name   string
		digest string
		want   string
	}{
		{
			name:   "standard prefix",
			digest: "sha256:aabbccddee0011223344556677889900aabbccddee0011223344556677889900",
			want:   "sha256/aa/aabbccddee0011223344556677889900aabbccddee0011223344556677889900",
		},
		{
			name:   "leading zeros",
			digest: "sha256:00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
			want:   "sha256/00/00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
		},
		{
			name:   "ff prefix",
			digest: "sha256:ff00000000000000000000000000000000000000000000000000000000000000",
			want:   "sha256/ff/ff00000000000000000000000000000000000000000000000000000000000000",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dgst := digest.Digest(tt.digest)
			got := storage.ContentPath(dgst)
			if got != tt.want {
				t.Errorf("ContentPath(%q) = %q, want %q", tt.digest, got, tt.want)
			}
		})
	}
}

func TestUploadPath(t *testing.T) {
	got := storage.UploadPath("ee160658-9444-4950-8ec6-30faab40529c")
	want := "uploads/ee160658-9444-4950-8ec6-30faab40529c"
	if got != want {
		t.Errorf("UploadPath() = %q, want %q", got, want)
	}
}

func TestDigestFromPathRoundTrip(t *testing.T) {
	digests := []string{
		"sha256:aabbccddee0011223344556677889900aabbccddee0011223344556677889900",
		"sha256:00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
	}
	for _, d := range digests {
		dgst := digest.Digest(d)
		path := storage.ContentPath(dgst)
		got, err := storage.DigestFromPath(path)
		if err != nil {
			t.Fatalf("DigestFromPath(%q): %v", path, err)
		}
		if got != dgst {
			t.Errorf("DigestFromPath(ContentPath(%q)) = %q, want %q", d, got, dgst)
		}
	}
}

func TestDigestFromPathInvalid(t *testing.T) {
	bad := []string{"", "noslash", "sha256", "sha256/tooshort"}
	for _, p := range bad {
		if _, err := storage.DigestFromPath(p); err == nil {
			t.Errorf("DigestFromPath(%q) should have returned error", p)
		}
	}
}
