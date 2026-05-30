package cmd

import (
	"bufio"
	"context"
	"crypto/rand"
	"crypto/x509"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"strings"
	"time"

	"github.com/quay/quay/internal/registry"
)

const (
	defaultImage       = "quay.io/quay/quay-mirror:latest"
	quadletServiceName = "quay"
)

func runInstall(args []string) int {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	hostname := fs.String("hostname", "", "server hostname for TLS and config (required)")
	dataDir := fs.String("data-dir", "/var/lib/quay", "directory for database, storage, and certs")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	image := fs.String("image", defaultImage, "container image to use")

	if err := fs.Parse(args); err != nil {
		return 1
	}

	if err := validateInstallFlags(fs, *hostname); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// Load or pull container image. Use the resolved reference for the Quadlet
	// since podman load may produce a different name:tag than --image.
	resolvedImage, err := loadOrPullImage(*imageArchive, *image)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// Check if Quadlet file already exists.
	isRoot := os.Getuid() == 0
	quadletPath, err := resolveQuadletPath(isRoot)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error resolving quadlet path: %v\n", err)
		return 1
	}

	if _, err := os.Stat(quadletPath); err == nil {
		// Upgrade path: Quadlet exists, update the image.
		fmt.Fprintln(os.Stderr, "existing installation detected — upgrading...")

		svcArgs := systemctlArgs(isRoot)

		// Stop the service.
		fmt.Fprintln(os.Stderr, "stopping registry...")
		if err := runCmd("systemctl", append(svcArgs, "stop", quadletServiceName)...); err != nil {
			fmt.Fprintf(os.Stderr, "error stopping service: %v\n", err)
			return 1
		}

		// Update Quadlet file with new image.
		if err := updateQuadletImage(quadletPath, resolvedImage); err != nil {
			fmt.Fprintf(os.Stderr, "error updating quadlet: %v\n", err)
			return 1
		}
		fmt.Fprintf(os.Stderr, "updated quadlet: %s\n", quadletPath)

		// Reload and start.
		if err := runCmd("systemctl", append(svcArgs, "daemon-reload")...); err != nil {
			fmt.Fprintf(os.Stderr, "error reloading systemd: %v\n", err)
			return 1
		}
		if err := runCmd("systemctl", append(svcArgs, "start", quadletServiceName)...); err != nil {
			fmt.Fprintf(os.Stderr, "error starting service: %v\n", err)
			return 1
		}
	} else {
		// Fresh install: Create directory structure and Quadlet file.
		storageDir := filepath.Join(*dataDir, "storage")
		for _, dir := range []string{*dataDir, storageDir} {
			if err := os.MkdirAll(dir, 0o750); err != nil {
				fmt.Fprintf(os.Stderr, "error creating directory %s: %v\n", dir, err)
				return 1
			}
		}

		// Write Quadlet file and start service.
		if err := installQuadlet(resolvedImage, *dataDir, *hostname); err != nil {
			fmt.Fprintf(os.Stderr, "error installing service: %v\n", err)
			return 1
		}
	}

	// Health check.
	credPath := filepath.Join(*dataDir, "credentials")
	healthURL := fmt.Sprintf("https://%s:8443/healthz", *hostname)
	certPath := filepath.Join(*dataDir, "ssl.cert")

	fmt.Fprintln(os.Stderr, "waiting for registry to start...")
	if err := waitForHealth(healthURL, certPath, 30*time.Second); err != nil {
		fmt.Fprintf(os.Stderr, "error: health check failed: %v\n", err)
		fmt.Fprintln(os.Stderr, "check: systemctl status quay")
		return 1
	}

	fmt.Fprintf(os.Stderr, "\nregistry running at https://%s:8443\n", *hostname)
	fmt.Fprintf(os.Stderr, "credentials: %s\n", credPath)
	return 0
}

func systemctlArgs(isRoot bool) []string {
	if isRoot {
		return nil
	}
	return []string{"--user"}
}

func resolveQuadletPath(isRoot bool) (string, error) {
	if isRoot {
		return "/etc/containers/systemd/quay.container", nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("determine home directory: %w", err)
	}
	return filepath.Join(home, ".config", "containers", "systemd", "quay.container"), nil
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

func validateInstallFlags(fs *flag.FlagSet, hostname string) error {
	if hostname == "" {
		fs.Usage()
		return fmt.Errorf("--hostname is required")
	}
	return validateHostname(hostname)
}

func validateHostname(hostname string) error {
	if len(hostname) > 253 {
		return fmt.Errorf("exceeds 253 characters (got %d)", len(hostname))
	}
	if net.ParseIP(hostname) != nil {
		return nil
	}
	labels := strings.Split(hostname, ".")
	for _, label := range labels {
		if len(label) == 0 {
			return fmt.Errorf("contains empty label")
		}
		if len(label) > 63 {
			return fmt.Errorf("label %q exceeds 63 characters", label)
		}
		if !isAlphanumeric(label[0]) || !isAlphanumeric(label[len(label)-1]) {
			return fmt.Errorf("label %q must start and end with alphanumeric character", label)
		}
		for _, c := range label {
			if !isAlphanumeric(byte(c)) && c != '-' {
				return fmt.Errorf("label %q contains invalid character %q", label, c)
			}
		}
	}
	return nil
}

func isAlphanumeric(c byte) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
}

func loadOrPullImage(imageArchive, image string) (string, error) {
	if imageArchive != "" {
		fmt.Fprintf(os.Stderr, "loading container image from %s\n", imageArchive)
		ref, err := runCmdOutput("podman", "load", "-i", imageArchive)
		if err != nil {
			return "", fmt.Errorf("loading image: %w", err)
		}
		loaded := parseLoadedImageRef(ref)
		if loaded == "" {
			return "", fmt.Errorf("could not determine image reference from podman load output")
		}
		fmt.Fprintf(os.Stderr, "loaded image: %s\n", loaded)
		return loaded, nil
	}
	fmt.Fprintf(os.Stderr, "pulling container image %s\n", image)
	if err := runCmd("podman", "pull", image); err != nil {
		return "", fmt.Errorf("pulling image: %w", err)
	}
	return image, nil
}

func runCmdOutput(name string, args ...string) (string, error) {
	cmd := exec.CommandContext(context.Background(), name, args...) //nolint:gosec // CLI tool, args from flags
	cmd.Stderr = os.Stderr
	out, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

// parseLoadedImageRef extracts the image reference from podman load output.
// podman load prints "Loaded image: <ref>" or "Loaded image(s): <ref>".
func parseLoadedImageRef(output string) string {
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

func installQuadlet(image, dataDir, hostname string) error {
	isRoot := os.Getuid() == 0

	var quadletDir string
	if isRoot {
		quadletDir = "/etc/containers/systemd"
	} else {
		home, err := os.UserHomeDir()
		if err != nil {
			return fmt.Errorf("get home dir: %w", err)
		}
		quadletDir = filepath.Join(home, ".config", "containers", "systemd")
	}

	if err := os.MkdirAll(quadletDir, 0o750); err != nil {
		return fmt.Errorf("create quadlet dir: %w", err)
	}

	quadletContent := fmt.Sprintf(`[Unit]
Description=Quay OCI Registry
After=network-online.target

[Container]
Image=%s
Volume=%s:/data:Z
PublishPort=8443:8443
Exec=serve --data-dir /data --hostname %s

[Install]
WantedBy=default.target
`, image, dataDir, hostname)

	quadletPath := filepath.Join(quadletDir, "quay.container")
	if err := os.WriteFile(quadletPath, []byte(quadletContent), 0o600); err != nil {
		return fmt.Errorf("write quadlet: %w", err)
	}
	fmt.Fprintf(os.Stderr, "quadlet: %s\n", quadletPath)

	// Reload and start.
	if isRoot {
		if err := runCmd("systemctl", "daemon-reload"); err != nil {
			return err
		}
		if err := runCmd("systemctl", "enable", "--now", quadletServiceName); err != nil {
			return err
		}
	} else {
		if err := runCmd("systemctl", "--user", "daemon-reload"); err != nil {
			return err
		}
		if err := runCmd("systemctl", "--user", "enable", "--now", quadletServiceName); err != nil {
			return err
		}
		// Enable linger so user services survive logout.
		if u, err := user.Current(); err == nil {
			_ = runCmd("loginctl", "enable-linger", u.Username)
		}
	}

	return nil
}

func waitForHealth(url, certPath string, timeout time.Duration) error {
	caCert, err := os.ReadFile(certPath) //nolint:gosec // certPath is from known data directory
	if err != nil {
		return fmt.Errorf("read TLS certificate: %w", err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caCert) {
		return fmt.Errorf("parse TLS certificate: %s", certPath)
	}
	tlsCfg := registry.SecureTLSConfig()
	tlsCfg.RootCAs = pool
	client := &http.Client{
		Timeout: 2 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: tlsCfg,
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
			if resp.StatusCode == http.StatusOK {
				return nil
			}
		}
		time.Sleep(2 * time.Second)
	}
	return fmt.Errorf("timeout after %s", timeout)
}

func runCmd(name string, args ...string) error {
	cmd := exec.CommandContext(context.Background(), name, args...) //nolint:gosec // CLI tool, args from flags
	cmd.Stdout = os.Stderr
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// generatePassword creates a random password of the given length.
func generatePassword(length int) (string, error) {
	b := make([]byte, length)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	for i := range b {
		b[i] = charset[int(b[i])%len(charset)]
	}
	return string(b), nil
}

// generateUUID creates a UUID v4 using crypto/rand.
func generateUUID() (string, error) {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", err
	}
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:16]), nil
}
