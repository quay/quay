package system

import "testing"

func TestParseLoadedImageRef(t *testing.T) {
	tests := []struct {
		name   string
		output string
		want   string
	}{
		{
			name:   "standard podman output",
			output: "Loaded image: localhost/quay-mirror:test\n",
			want:   "localhost/quay-mirror:test",
		},
		{
			name:   "plural form",
			output: "Loaded image(s): docker.io/library/nginx:latest\n",
			want:   "docker.io/library/nginx:latest",
		},
		{
			name:   "with extra whitespace",
			output: "  Loaded image:   localhost/myimage:v1  \n",
			want:   "localhost/myimage:v1",
		},
		{
			name:   "multi-line with noise",
			output: "Getting image source signatures\nCopying blob sha256:abc123\nLoaded image: localhost/test:latest\n",
			want:   "localhost/test:latest",
		},
		{
			name:   "empty output",
			output: "",
			want:   "",
		},
		{
			name:   "no match",
			output: "some unrelated output\n",
			want:   "",
		},
		{
			name:   "no colon separator",
			output: "Loaded image without colon\n",
			want:   "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ParseLoadedImageRef(tt.output)
			if got != tt.want {
				t.Errorf("ParseLoadedImageRef(%q) = %q, want %q", tt.output, got, tt.want)
			}
		})
	}
}
