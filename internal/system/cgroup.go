package system

import (
	"context"
	"fmt"
	"os"
	"strings"
)

// CheckCgroupVersion returns the cgroups version reported by podman (e.g., "v1" or "v2").
func CheckCgroupVersion(ctx context.Context, runner CommandRunner) (string, error) {
	if runner == nil {
		return "", fmt.Errorf("no command runner available")
	}
	output, err := runner.Output(ctx, "podman", "info", "--format", "{{.Host.CgroupsVersion}}")
	if err != nil {
		return "", fmt.Errorf("check cgroups version: %w", err)
	}
	return strings.TrimSpace(output), nil
}

// ValidateCgroupsForQuadlet checks that the host meets the cgroups requirements
// for OMR 3.0. Rootless installs require cgroups v2; rootful installs work on
// both v1 and v2.
func ValidateCgroupsForQuadlet(ctx context.Context, runner CommandRunner) error {
	version, err := CheckCgroupVersion(ctx, runner)
	if err != nil {
		return nil
	}
	if version == "v2" {
		return nil
	}
	if os.Getuid() != 0 {
		return fmt.Errorf(
			"this host uses cgroups %s but OMR 3.0 requires cgroups v2 for rootless installs\n\n"+
				"To fix this, enable cgroups v2 and reboot:\n\n"+
				"  sudo grubby --update-kernel=ALL --args=\"systemd.unified_cgroup_hierarchy=1\"\n"+
				"  sudo reboot\n\n"+
				"After reboot, verify with:\n\n"+
				"  podman info --format '{{.Host.CgroupsVersion}}'\n\n"+
				"Then re-run this command. Your existing installation has not been modified.", version)
	}
	return nil
}
