package distribution_test

import (
	"os/exec"
	"strings"
	"testing"
)

func TestRuntimeHasNoProductSpecificDependencies(t *testing.T) {
	cmd := exec.CommandContext(t.Context(), "go", "list", "-deps", "github.com/quay/quay/internal/registry/distribution") //nolint:gosec // fixed package path
	output, err := cmd.Output()
	if err != nil {
		t.Fatalf("go list runtime dependencies: %v", err)
	}

	for _, dependency := range strings.Fields(string(output)) {
		if isProductSpecificDependency(dependency) {
			t.Errorf("shared runtime depends on product-specific package %s", dependency)
		}
	}
}

func isProductSpecificDependency(dependency string) bool {
	for _, prefix := range []string{
		"database/sql",
		"github.com/distribution/distribution/",
		"github.com/distribution/reference",
		"github.com/quay/quay/internal/dal/",
		"github.com/quay/quay/internal/mirrorregistry",
		"github.com/quay/quay/internal/oci/storage/local",
		"github.com/quay/quay/internal/registry/jwtauth",
		"github.com/quay/quay/internal/repository/dal",
		"github.com/openshift/",
	} {
		if strings.HasPrefix(dependency, prefix) {
			return true
		}
	}
	return false
}
