package system

import (
	"context"
	"fmt"
	"strings"
)

// ImageLoader abstracts container image loading/pulling.
type ImageLoader interface {
	Load(ctx context.Context, archivePath string) (imageRef string, err error)
	Pull(ctx context.Context, image string) error
}

// PodmanLoader implements ImageLoader using podman.
type PodmanLoader struct {
	runner CommandRunner
}

// NewPodmanLoader returns a PodmanLoader that delegates to runner.
func NewPodmanLoader(runner CommandRunner) *PodmanLoader {
	return &PodmanLoader{runner: runner}
}

// Load imports a container image from a tar archive via podman load.
func (p *PodmanLoader) Load(ctx context.Context, archivePath string) (string, error) {
	output, err := p.runner.Output(ctx, "podman", "load", "-i", archivePath)
	if err != nil {
		return "", fmt.Errorf("podman load: %w", err)
	}
	ref := ParseLoadedImageRef(output)
	if ref == "" {
		return "", fmt.Errorf("could not parse image reference from podman load output")
	}
	return ref, nil
}

// Pull fetches a container image from a remote registry via podman pull.
func (p *PodmanLoader) Pull(ctx context.Context, image string) error {
	if err := p.runner.Run(ctx, "podman", "pull", image); err != nil {
		return fmt.Errorf("podman pull: %w", err)
	}
	return nil
}

// ParseLoadedImageRef extracts the image reference from podman load output.
// podman load prints "Loaded image: <ref>" or "Loaded image(s): <ref>".
func ParseLoadedImageRef(output string) string {
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "Loaded image") {
			if idx := strings.Index(line, ": "); idx >= 0 {
				return strings.TrimSpace(line[idx+2:])
			}
		}
	}
	return ""
}
