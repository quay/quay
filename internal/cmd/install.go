package cmd

import (
	"context"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"database/sql"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/crypto/bcrypt"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
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
	adminUser := fs.String("admin-username", "admin", "admin username")
	adminEmail := fs.String("admin-email", "", "admin email (default: admin@<hostname>)")
	adminPass := fs.String("admin-password", "", "admin password (auto-generated if empty)")
	sslCert := fs.String("ssl-cert", "", "path to custom TLS certificate")
	sslKey := fs.String("ssl-key", "", "path to custom TLS key")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	image := fs.String("image", defaultImage, "container image to use")

	if err := fs.Parse(args); err != nil {
		return 1
	}

	if err := validateInstallFlags(fs, *hostname, *sslCert, *sslKey); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	passwordGenerated := false
	if *adminPass == "" {
		generated, err := generatePassword(32)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error generating password: %v\n", err)
			return 1
		}
		*adminPass = generated
		passwordGenerated = true
	}

	if *adminEmail == "" {
		*adminEmail = fmt.Sprintf("%s@%s", *adminUser, *hostname)
	}

	// Create directory structure.
	storageDir := filepath.Join(*dataDir, "storage")
	for _, dir := range []string{*dataDir, storageDir} {
		if err := os.MkdirAll(dir, 0o750); err != nil {
			fmt.Fprintf(os.Stderr, "error creating directory %s: %v\n", dir, err)
			return 1
		}
	}

	// Load or pull container image. Use the resolved reference for the Quadlet
	// since podman load may produce a different name:tag than --image.
	resolvedImage, err := loadOrPullImage(*imageArchive, *image)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// Generate config, init DB, create admin user.
	dbPath := filepath.Join(*dataDir, "quay.db")
	configPath := filepath.Join(*dataDir, "config.yaml")
	certPath := filepath.Join(*dataDir, "ssl.cert")
	keyPath := filepath.Join(*dataDir, "ssl.key")

	if err := writeConfig(configPath, *hostname); err != nil {
		fmt.Fprintf(os.Stderr, "error writing config: %v\n", err)
		return 1
	}
	fmt.Fprintf(os.Stderr, "config: %s\n", configPath)

	if err := initDBAndUser(dbPath, *adminUser, *adminEmail, *adminPass); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	fmt.Fprintf(os.Stderr, "database: %s\n", dbPath)
	fmt.Fprintf(os.Stderr, "admin user: %s\n", *adminUser)

	// Show generated credentials immediately so they aren't lost if a later step fails.
	if passwordGenerated {
		fmt.Fprintf(os.Stderr, "admin credentials: %s / %s\n", *adminUser, *adminPass)
	}

	// TLS certificates.
	if err := setupCertificates(*sslCert, *sslKey, certPath, keyPath, *hostname); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	// Write Quadlet file and start service.
	if err := installQuadlet(resolvedImage, *dataDir); err != nil {
		fmt.Fprintf(os.Stderr, "error installing service: %v\n", err)
		return 1
	}

	// Health check.
	fmt.Fprintln(os.Stderr, "waiting for registry to start...")
	if err := waitForHealth(fmt.Sprintf("https://%s:8443/v2/", *hostname), certPath, 30*time.Second); err != nil {
		fmt.Fprintf(os.Stderr, "error: health check failed: %v\n", err)
		fmt.Fprintln(os.Stderr, "check: systemctl status quay")
		return 1
	}

	fmt.Fprintf(os.Stderr, "\nregistry running at https://%s:8443\n", *hostname)
	return 0
}

func validateInstallFlags(fs *flag.FlagSet, hostname, sslCert, sslKey string) error {
	if hostname == "" {
		fs.Usage()
		return fmt.Errorf("--hostname is required")
	}
	if (sslCert == "") != (sslKey == "") {
		return fmt.Errorf("--ssl-cert and --ssl-key must both be provided together")
	}
	return nil
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

func writeConfig(configPath, hostname string) error {
	configContent := fmt.Sprintf(`SERVER_HOSTNAME: %s
PREFERRED_URL_SCHEME: https
DB_URI: sqlite:///quay.db
DISTRIBUTED_STORAGE_CONFIG:
  default:
    - LocalStorage
    - storage_path: storage
DEFAULT_TAG_EXPIRATION: 2w
`, hostname)

	return os.WriteFile(configPath, []byte(configContent), 0o600)
}

func initDBAndUser(dbPath, adminUser, adminEmail, adminPass string) error {
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		return fmt.Errorf("opening database: %w", err)
	}
	defer func() { _ = db.Close() }()

	ctx := context.Background()
	if err := dbcore.InitDatabase(ctx, db, os.Stderr); err != nil {
		return fmt.Errorf("initializing database: %w", err)
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(adminPass), bcrypt.DefaultCost)
	if err != nil {
		return fmt.Errorf("hashing password: %w", err)
	}

	uuid, err := generateUUID()
	if err != nil {
		return fmt.Errorf("generating UUID: %w", err)
	}

	queries := daldb.New(db)
	if _, err := queries.CreateAdminUser(ctx, daldb.CreateAdminUserParams{
		Uuid:         sql.NullString{String: uuid, Valid: true},
		Username:     adminUser,
		PasswordHash: sql.NullString{String: string(hash), Valid: true},
		Email:        adminEmail,
	}); err != nil {
		return fmt.Errorf("creating admin user: %w", err)
	}

	return nil
}

func setupCertificates(sslCert, sslKey, certPath, keyPath, hostname string) error {
	if sslCert != "" && sslKey != "" {
		if err := copyFile(sslCert, certPath); err != nil {
			return fmt.Errorf("copying cert: %w", err)
		}
		if err := copyFile(sslKey, keyPath); err != nil {
			return fmt.Errorf("copying key: %w", err)
		}
		fmt.Fprintln(os.Stderr, "tls: copied user-provided certificate")
	} else {
		if err := registry.GenerateSelfSignedCert(hostname, certPath, keyPath); err != nil {
			return fmt.Errorf("generating certificate: %w", err)
		}
		fmt.Fprintf(os.Stderr, "tls: generated self-signed certificate for %s\n", hostname)
	}
	return nil
}

func installQuadlet(image, dataDir string) error {
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
Exec=serve --config /data/config.yaml

[Install]
WantedBy=default.target
`, image, dataDir)

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

func runCmd(name string, args ...string) error {
	cmd := exec.CommandContext(context.Background(), name, args...) //nolint:gosec // CLI tool, args from flags
	cmd.Stdout = os.Stderr
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func copyFile(src, dst string) error {
	data, err := os.ReadFile(src) //nolint:gosec // CLI tool, path from caller
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0o600) //nolint:gosec // data from known source file
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
