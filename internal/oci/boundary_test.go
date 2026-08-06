package oci_test

import (
	"encoding/json"
	"errors"
	"io"
	"os/exec"
	"strings"
	"testing"
)

type goPackage struct {
	ImportPath string
	Imports    []string
}

func TestNoDirectDistributionOutsideCompositionPackages(t *testing.T) {
	cmd := exec.CommandContext(t.Context(), "go", "list", "-json", "github.com/quay/quay/internal/...") //nolint:gosec // fixed package pattern
	output, err := cmd.Output()
	if err != nil {
		t.Fatalf("go list ./internal/...: %v", err)
	}

	decoder := json.NewDecoder(strings.NewReader(string(output)))
	for {
		var pkg goPackage
		if err := decoder.Decode(&pkg); err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			t.Fatalf("decode go list output: %v", err)
		}
		if distributionBoundaryExempt(pkg.ImportPath) {
			continue
		}
		for _, imported := range pkg.Imports {
			if isDistributionImport(imported) {
				t.Errorf("package %s directly imports %s — distribution must be confined to composition packages", pkg.ImportPath, imported)
			}
		}
	}
}

func distributionBoundaryExempt(importPath string) bool {
	short := strings.TrimPrefix(importPath, "github.com/quay/quay/")
	return strings.HasPrefix(short, "internal/registry/") ||
		short == "internal/registry" ||
		strings.HasPrefix(short, "internal/oci/storage/local/") ||
		short == "internal/oci/storage/local"
}

func isDistributionImport(importPath string) bool {
	return strings.HasPrefix(importPath, "github.com/distribution/distribution/") ||
		strings.HasPrefix(importPath, "github.com/distribution/reference")
}
