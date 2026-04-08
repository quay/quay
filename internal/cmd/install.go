package cmd

import (
	"context"
	"crypto/tls"
	"database/sql"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
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
	adminPass := fs.String("admin-password", "", "admin password (required)")
	sslCert := fs.String("ssl-cert", "", "path to custom TLS certificate")
	sslKey := fs.String("ssl-key", "", "path to custom TLS key")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	image := fs.String("image", defaultImage, "container image to use")

	if err := fs.Parse(args); err != nil {
		return 1
	}

	if *hostname == "" || *adminPass == "" {
		fmt.Fprintln(os.Stderr, "error: --hostname and --admin-password are required")
		fs.Usage()
		return 1
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

	// Load or pull container image.
	if *imageArchive != "" {
		fmt.Fprintf(os.Stderr, "loading container image from %s\n", *imageArchive)
		if err := runCmd("podman", "load", "-i", *imageArchive); err != nil {
			fmt.Fprintf(os.Stderr, "error loading image: %v\n", err)
			return 1
		}
	} else {
		fmt.Fprintf(os.Stderr, "pulling container image %s\n", *image)
		if err := runCmd("podman", "pull", *image); err != nil {
			fmt.Fprintf(os.Stderr, "error pulling image: %v\n", err)
			return 1
		}
	}

	// Generate config.yaml.
	dbPath := filepath.Join(*dataDir, "quay.db")
	configPath := filepath.Join(*dataDir, "config.yaml")
	certPath := filepath.Join(*dataDir, "ssl.cert")
	keyPath := filepath.Join(*dataDir, "ssl.key")

	configContent := fmt.Sprintf(`SERVER_HOSTNAME: %s
PREFERRED_URL_SCHEME: https
DB_URI: sqlite:////data/quay.db
DISTRIBUTED_STORAGE_CONFIG:
  default:
    - LocalStorage
    - storage_path: /data/storage
DEFAULT_TAG_EXPIRATION: 2w
`, *hostname)

	if err := os.WriteFile(configPath, []byte(configContent), 0o640); err != nil {
		fmt.Fprintf(os.Stderr, "error writing config: %v\n", err)
		return 1
	}
	fmt.Fprintf(os.Stderr, "config: %s\n", configPath)

	// Initialize database.
	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error opening database: %v\n", err)
		return 1
	}

	ctx := context.Background()
	if err := dbcore.InitDatabase(ctx, db, os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "error initializing database: %v\n", err)
		db.Close()
		return 1
	}
	fmt.Fprintf(os.Stderr, "database: %s\n", dbPath)

	// Create admin user.
	hash, err := bcrypt.GenerateFromPassword([]byte(*adminPass), bcrypt.DefaultCost)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error hashing password: %v\n", err)
		db.Close()
		return 1
	}

	uuid, err := generateUUID()
	if err != nil {
		fmt.Fprintf(os.Stderr, "error generating UUID: %v\n", err)
		db.Close()
		return 1
	}

	queries := daldb.New(db)
	if _, err := queries.CreateAdminUser(ctx, daldb.CreateAdminUserParams{
		Uuid:         sql.NullString{String: uuid, Valid: true},
		Username:     *adminUser,
		PasswordHash: sql.NullString{String: string(hash), Valid: true},
		Email:        *adminEmail,
	}); err != nil {
		fmt.Fprintf(os.Stderr, "error creating admin user: %v\n", err)
		db.Close()
		return 1
	}
	db.Close()
	fmt.Fprintf(os.Stderr, "admin user: %s\n", *adminUser)

	// TLS certificates.
	if *sslCert != "" && *sslKey != "" {
		if err := copyFile(*sslCert, certPath); err != nil {
			fmt.Fprintf(os.Stderr, "error copying cert: %v\n", err)
			return 1
		}
		if err := copyFile(*sslKey, keyPath); err != nil {
			fmt.Fprintf(os.Stderr, "error copying key: %v\n", err)
			return 1
		}
		fmt.Fprintln(os.Stderr, "tls: copied user-provided certificate")
	} else {
		if err := registry.GenerateSelfSignedCert(*hostname, certPath, keyPath); err != nil {
			fmt.Fprintf(os.Stderr, "error generating certificate: %v\n", err)
			return 1
		}
		fmt.Fprintf(os.Stderr, "tls: generated self-signed certificate for %s\n", *hostname)
	}

	// Write Quadlet file and start service.
	if err := installQuadlet(*image, *dataDir); err != nil {
		fmt.Fprintf(os.Stderr, "error installing service: %v\n", err)
		return 1
	}

	// Health check.
	fmt.Fprintln(os.Stderr, "waiting for registry to start...")
	if err := waitForHealth(fmt.Sprintf("https://%s:8443/v2/", *hostname), 30*time.Second); err != nil {
		fmt.Fprintf(os.Stderr, "warning: health check failed: %v\n", err)
		fmt.Fprintln(os.Stderr, "the registry may still be starting — check: systemctl status quay")
	} else {
		fmt.Fprintf(os.Stderr, "\nregistry running at https://%s:8443\n", *hostname)
	}

	fmt.Fprintf(os.Stderr, "admin credentials: %s / <password>\n", *adminUser)
	return 0
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
		quadletDir = filepath.Join(home, ".config/containers/systemd")
	}

	if err := os.MkdirAll(quadletDir, 0o755); err != nil {
		return fmt.Errorf("create quadlet dir: %w", err)
	}

	quadletContent := fmt.Sprintf(`[Unit]
Description=Quay OCI Registry
After=network-online.target

[Container]
Image=%s
Volume=%s:/data
PublishPort=8443:8443
Exec=serve --config /data/config.yaml

[Install]
WantedBy=default.target
`, image, dataDir)

	quadletPath := filepath.Join(quadletDir, "quay.container")
	if err := os.WriteFile(quadletPath, []byte(quadletContent), 0o644); err != nil {
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

func waitForHealth(url string, timeout time.Duration) error {
	client := &http.Client{
		Timeout: 2 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true}, //nolint:gosec // health check against self-signed cert
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

func runCmd(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Stdout = os.Stderr
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0o600)
}
