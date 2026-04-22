package cmd

import (
	"bufio"
	"context"
	"crypto/tls"
	"crypto/x509"
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
	quadletPath := resolveQuadletPath(isRoot)
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

	// 6. Health check.
	hostname := readHostnameFromConfig(filepath.Join(*dataDir, "config.yaml"))
	healthURL := fmt.Sprintf("https://%s:8443/v2/", hostname)
	certPath := filepath.Join(*dataDir, "ssl.cert")

	fmt.Fprintln(os.Stderr, "waiting for registry...")
	if err := waitForHealthCheck(healthURL, certPath, 30*time.Second); err != nil {
		fmt.Fprintf(os.Stderr, "error: health check failed: %v\n", err)
		fmt.Fprintln(os.Stderr, "check: systemctl status quay")
		return 1
	}

	fmt.Fprintf(os.Stderr, "upgrade complete — registry running at https://%s:8443\n", hostname)
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
	home, err := os.UserHomeDir()
	if err != nil {
		return filepath.Join(".", ".config", "containers", "systemd", "quay.container")
	}
	return filepath.Join(home, ".config", "containers", "systemd", "quay.container")
}

func updateQuadletImage(quadletPath, newImage string) error {
	data, err := os.ReadFile(quadletPath) //nolint:gosec // path from known quadlet location
	if err != nil {
		return fmt.Errorf("read quadlet: %w", err)
	}

	var updated []string
	found := false
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "Image=") {
			updated = append(updated, "Image="+newImage)
			found = true
		} else {
			updated = append(updated, line)
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("scan quadlet: %w", err)
	}
	if !found {
		return fmt.Errorf("no Image= directive found in %s", quadletPath)
	}

	return os.WriteFile(quadletPath, []byte(strings.Join(updated, "\n")+"\n"), 0o600) //nolint:gosec // quadlet path is known
}

func readHostnameFromConfig(configPath string) string {
	data, err := os.ReadFile(configPath) //nolint:gosec // path from known data dir
	if err != nil {
		return defaultHostname
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "SERVER_HOSTNAME:") {
			return strings.TrimSpace(strings.TrimPrefix(line, "SERVER_HOSTNAME:"))
		}
	}
	return defaultHostname
}

func waitForHealthCheck(url, certPath string, timeout time.Duration) error {
	caCert, err := os.ReadFile(certPath) //nolint:gosec // certPath is from known data directory
	if err != nil {
		return fmt.Errorf("read TLS certificate: %w", err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caCert) {
		return fmt.Errorf("parse TLS certificate: %s", certPath)
	}
	client := &http.Client{
		Timeout: 2 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{RootCAs: pool, MinVersion: tls.VersionTLS12},
		},
	}
	ctx := context.Background()
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, http.NoBody)
		if err != nil {
			return fmt.Errorf("create request: %w", err)
		}
		resp, err := client.Do(req)
		if err == nil {
			_ = resp.Body.Close()
			if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusUnauthorized {
				return nil
			}
		}
		time.Sleep(2 * time.Second)
	}
	return fmt.Errorf("timeout after %s", timeout)
}
