package cmd

import (
	"bufio"
	"crypto/tls"
	"flag"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
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

	// 1. Stop the service.
	fmt.Fprintln(os.Stderr, "stopping registry...")
	if err := runCmd("systemctl", append(svcArgs, "stop", quadletServiceName)...); err != nil {
		fmt.Fprintf(os.Stderr, "error stopping service: %v\n", err)
		return 1
	}

	// 2. Load or pull the new image.
	if *imageArchive != "" {
		fmt.Fprintf(os.Stderr, "loading image from %s\n", *imageArchive)
		if err := runCmd("podman", "load", "-i", *imageArchive); err != nil {
			fmt.Fprintf(os.Stderr, "error loading image: %v\n", err)
			return 1
		}
	} else {
		fmt.Fprintf(os.Stderr, "pulling image %s\n", *image)
		if err := runCmd("podman", "pull", *image); err != nil {
			fmt.Fprintf(os.Stderr, "error pulling image: %v\n", err)
			return 1
		}
	}

	// 3. Run db upgrade using the new image.
	fmt.Fprintln(os.Stderr, "upgrading database...")
	if err := runCmd("podman", "run", "--rm",
		"-v", *dataDir+":/data",
		*image,
		"db", "upgrade", "--config", "/data/config.yaml",
	); err != nil {
		fmt.Fprintf(os.Stderr, "error upgrading database: %v\n", err)
		fmt.Fprintln(os.Stderr, "the service is stopped — restore from backup if needed")
		return 1
	}

	// 4. Update Quadlet file with new image.
	quadletPath := resolveQuadletPath(isRoot)
	if err := updateQuadletImage(quadletPath, *image); err != nil {
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

	// 6. Health check.
	hostname := readHostnameFromConfig(filepath.Join(*dataDir, "config.yaml"))
	healthURL := fmt.Sprintf("https://%s:8443/v2/", hostname)

	fmt.Fprintln(os.Stderr, "waiting for registry...")
	if err := waitForHealthCheck(healthURL, 30*time.Second); err != nil {
		fmt.Fprintf(os.Stderr, "warning: health check failed: %v\n", err)
		fmt.Fprintln(os.Stderr, "check: systemctl status quay")
	} else {
		fmt.Fprintf(os.Stderr, "upgrade complete — registry running at https://%s:8443\n", hostname)
	}

	return 0
}

func systemctlArgs(isRoot bool) []string {
	if isRoot {
		return nil
	}
	return []string{"--user"}
}

func resolveQuadletPath(isRoot bool) string {
	if isRoot {
		return "/etc/containers/systemd/quay.container"
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".config/containers/systemd/quay.container")
}

func updateQuadletImage(quadletPath, newImage string) error {
	data, err := os.ReadFile(quadletPath)
	if err != nil {
		return fmt.Errorf("read quadlet: %w", err)
	}

	var updated []string
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "Image=") {
			updated = append(updated, "Image="+newImage)
		} else {
			updated = append(updated, line)
		}
	}

	return os.WriteFile(quadletPath, []byte(strings.Join(updated, "\n")+"\n"), 0o644)
}

func readHostnameFromConfig(configPath string) string {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return "localhost"
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "SERVER_HOSTNAME:") {
			return strings.TrimSpace(strings.TrimPrefix(line, "SERVER_HOSTNAME:"))
		}
	}
	return "localhost"
}

func waitForHealthCheck(url string, timeout time.Duration) error {
	client := &http.Client{
		Timeout: 2 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true}, //nolint:gosec // self-signed cert
		},
	}
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		resp, err := client.Get(url)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusUnauthorized {
				return nil
			}
		}
		time.Sleep(2 * time.Second)
	}
	return fmt.Errorf("timeout after %s", timeout)
}
