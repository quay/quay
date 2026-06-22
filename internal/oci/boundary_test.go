package oci_test

import (
	"os/exec"
	"strings"
	"testing"
)

func TestNoDistributionOutsideRegistry(t *testing.T) {
	// Dynamically discover all internal/ packages, then verify that only
	// internal/registry/... and internal/cmd/... (composition root) may
	// depend on distribution.
	allPkgs, err := exec.CommandContext(t.Context(), "go", "list", "github.com/quay/quay/internal/...").Output()
	if err != nil {
		t.Fatalf("go list ./internal/...: %v", err)
	}

	for _, pkg := range strings.Split(strings.TrimSpace(string(allPkgs)), "\n") {
		if pkg == "" {
			continue
		}
		// These packages are allowed to import distribution.
		short := strings.TrimPrefix(pkg, "github.com/quay/quay/")
		if strings.HasPrefix(short, "internal/registry/") || short == "internal/registry" ||
			strings.HasPrefix(short, "internal/cmd/") || short == "internal/cmd" ||
			strings.HasPrefix(short, "internal/oci/storage/local/") || short == "internal/oci/storage/local" {
			continue
		}

		out, err := exec.CommandContext(t.Context(), "go", "list", "-deps", pkg).Output() //nolint:gosec // trusted input
		if err != nil {
			t.Fatalf("go list -deps %s: %v", pkg, err)
		}
		for _, dep := range strings.Split(string(out), "\n") {
			if strings.Contains(dep, "distribution/distribution") ||
				strings.Contains(dep, "distribution/reference") {
				t.Errorf("package %s depends on %s — distribution must be confined to internal/registry/", pkg, dep)
			}
		}
	}
}
