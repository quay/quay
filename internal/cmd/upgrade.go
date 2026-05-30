package cmd

import (
	"flag"
	"fmt"
	"os"
)

func runUpgrade(args []string) int {
	fs := flag.NewFlagSet("upgrade", flag.ContinueOnError)
	image := fs.String("image", defaultImage, "new container image")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	dataDir := fs.String("data-dir", "/var/lib/quay", "data directory")

	if err := fs.Parse(args); err != nil {
		return 1
	}

	isRoot := os.Getuid() == 0
	svcArgs := systemctlArgs(isRoot)

	// 1. Load or pull the new image BEFORE stopping the service,
	// so a network/archive failure doesn't leave the registry offline.
	resolvedImage, err := loadOrPullImage(*imageArchive, *image)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// 2. Stop the service.
	fmt.Fprintln(os.Stderr, "stopping registry...")
	if err := runCmd("systemctl", append(svcArgs, "stop", quadletServiceName)...); err != nil {
		fmt.Fprintf(os.Stderr, "error stopping service: %v\n", err)
		return 1
	}

	// 3. Run db upgrade using the new image.
	fmt.Fprintln(os.Stderr, "upgrading database...")
	if err := runCmd("podman", "run", "--rm",
		"-v", *dataDir+":/data:Z",
		resolvedImage,
		"_db", "upgrade", "--config", "/data/config.yaml",
	); err != nil {
		fmt.Fprintf(os.Stderr, "error upgrading database: %v\n", err)
		fmt.Fprintln(os.Stderr, "the service is stopped — restore from backup if needed")
		return 1
	}

	// 4. Update Quadlet file with new image.
	quadletPath, err := resolveQuadletPath(isRoot)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error resolving quadlet path: %v\n", err)
		return 1
	}
	if err := updateQuadletImage(quadletPath, resolvedImage); err != nil {
		fmt.Fprintf(os.Stderr, "error updating quadlet: %v\n", err)
		return 1
	}
	fmt.Fprintf(os.Stderr, "updated quadlet: %s\n", quadletPath)

	// 5. Reload and start.
	if err := runCmd("systemctl", append(svcArgs, "daemon-reload")...); err != nil {
		fmt.Fprintf(os.Stderr, "error reloading systemd: %v\n", err)
		return 1
	}
	if err := runCmd("systemctl", append(svcArgs, "start", quadletServiceName)...); err != nil {
		fmt.Fprintf(os.Stderr, "error starting service: %v\n", err)
		return 1
	}

	fmt.Fprintln(os.Stderr, "upgrade complete — restart complete")
	return 0
}
