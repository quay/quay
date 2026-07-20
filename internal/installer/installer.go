// Package installer implements the install and upgrade workflow for the
// registry's Quadlet-based systemd deployment.
package installer

import (
	"context"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"github.com/quay/quay/internal/bootstrap"
	"github.com/quay/quay/internal/certs"
	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/system"
)

const (
	// DefaultImage is the default container image for the registry.
	DefaultImage = "quay.io/quay/quay-mirror:latest"

	defaultPort         = "8443"
	defaultInitUsername = "admin"
	quadletServiceName  = "quay"
)

// Config holds the parameters for an install or upgrade operation.
type Config struct {
	Hostname                    string
	DataDir                     string
	ImageArchive                string
	Image                       string
	ConfigPath                  string
	Port                        string
	SSLCert                     string
	SSLKey                      string
	SSLSkipHostnameVerification bool
	InitUser                    string
	InitPassword                string
	InitPasswordSet             bool
}

// Installer orchestrates fresh installs and upgrades of the registry
// as a Quadlet systemd service.
type Installer struct {
	images  system.ImageLoader
	runner  system.CommandRunner
	systemd system.ServiceManager
	quadlet *system.QuadletManager
	env     *system.Env
	fs      system.FileSystem
}

// New detects the runtime environment and creates an Installer with the
// appropriate system backends.
func New(stderr io.Writer) (*Installer, error) {
	env, err := system.NewEnv()
	if err != nil {
		return nil, fmt.Errorf("detect environment: %w", err)
	}

	runner := system.NewExecRunner(stderr)
	fs := system.OSFS{}

	return &Installer{
		images:  system.NewPodmanLoader(runner),
		runner:  runner,
		systemd: system.NewSystemdManager(runner, env),
		quadlet: system.NewQuadletManager(fs, env),
		env:     env,
		fs:      fs,
	}, nil
}

// Initialize performs the one-shot initialization used by both `quay init`
// and `quay install`, without starting a long-running server or container.
func Initialize(ctx context.Context, cfg *Config) error {
	if cfg == nil {
		return fmt.Errorf("nil installer config")
	}
	resolvedCfg := *cfg
	if resolvedCfg.InitUser == "" {
		resolvedCfg.InitUser = defaultInitUsername
	}
	if err := validateInitConfig(&resolvedCfg); err != nil {
		return fmt.Errorf("initial administrator: %w", err)
	}
	inst := &Installer{fs: system.OSFS{}}
	return inst.initialize(ctx, &resolvedCfg)
}

// Run performs an install or upgrade based on whether a Quadlet unit already
// exists.
func (inst *Installer) Run(ctx context.Context, cfg *Config) error {
	if cfg == nil {
		return fmt.Errorf("nil installer config")
	}

	resolvedCfg := *cfg
	if resolvedCfg.InitUser == "" {
		resolvedCfg.InitUser = defaultInitUsername
	}
	if err := validateInitConfig(&resolvedCfg); err != nil {
		return fmt.Errorf("initial administrator: %w", err)
	}

	upgrading := inst.quadlet.Exists(quadletServiceName)
	port, err := inst.resolvePort(cfg.Port, upgrading)
	if err != nil {
		return fmt.Errorf("resolve port: %w", err)
	}
	resolvedCfg.Port = port

	if err := inst.initialize(ctx, &resolvedCfg); err != nil {
		return fmt.Errorf("initialize registry: %w", err)
	}

	imageRef, err := inst.resolveImage(ctx, resolvedCfg.ImageArchive, resolvedCfg.Image)
	if err != nil {
		return fmt.Errorf("image resolution: %w", err)
	}

	if upgrading {
		if err := inst.upgrade(ctx, &resolvedCfg, imageRef, port); err != nil {
			return fmt.Errorf("upgrade: %w", err)
		}
	} else {
		if err := inst.freshInstall(ctx, &resolvedCfg, imageRef); err != nil {
			return fmt.Errorf("install: %w", err)
		}
	}

	healthURL := fmt.Sprintf("https://%s:%s/healthz", resolvedCfg.Hostname, port)
	certPath := filepath.Join(resolvedCfg.DataDir, "ssl.cert")
	slog.Info("waiting for registry to start")
	if err := inst.waitForHealth(ctx, healthURL, certPath, resolvedCfg.SSLSkipHostnameVerification, 30*time.Second); err != nil {
		inst.dumpContainerLogs(ctx)
		return fmt.Errorf("health check: %w", err)
	}

	credPath := filepath.Join(resolvedCfg.DataDir, "auth", "admin-password")
	slog.Info("registry running", "url", fmt.Sprintf("https://%s:%s", resolvedCfg.Hostname, port), "credentials", credPath)
	return nil
}

func (inst *Installer) resolvePort(requestedPort string, upgrading bool) (string, error) {
	port := requestedPort
	if port == "" {
		if upgrading {
			var err error
			port, err = inst.quadlet.HostPort(quadletServiceName)
			if err != nil {
				return "", fmt.Errorf("determine existing port: %w", err)
			}
		} else {
			port = defaultPort
		}
	}
	if err := ValidatePort(port); err != nil {
		return "", err
	}
	return port, nil
}

func (inst *Installer) resolveImage(ctx context.Context, archive, image string) (string, error) {
	if archive != "" {
		slog.Info("loading container image", "archive", archive)
		ref, err := inst.images.Load(ctx, archive)
		if err != nil {
			return "", fmt.Errorf("loading image: %w", err)
		}
		slog.Info("loaded image", "ref", ref)
		return ref, nil
	}
	slog.Info("pulling container image", "image", image)
	if err := inst.images.Pull(ctx, image); err != nil {
		return "", fmt.Errorf("pulling image: %w", err)
	}
	return image, nil
}

func (inst *Installer) upgrade(ctx context.Context, cfg *Config, imageRef, port string) error {
	slog.Info("existing installation detected, upgrading")

	// Validate and install replacement TLS material before stopping the running
	// service. The process keeps its currently loaded pair until it is restarted.
	if cfg.SSLCert != "" {
		if err := inst.copyUserTLS(cfg); err != nil {
			return fmt.Errorf("TLS certificate setup: %w", err)
		}
	}

	slog.Info("stopping registry")
	if err := inst.systemd.Stop(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("stop service: %w", err)
	}

	if err := inst.quadlet.UpdateImageAndPort(quadletServiceName, imageRef, port); err != nil {
		return fmt.Errorf("update quadlet: %w", err)
	}
	slog.Info("updated quadlet", "path", inst.env.QuadletPath(quadletServiceName))

	if err := inst.systemd.DaemonReload(ctx); err != nil {
		return fmt.Errorf("reload systemd: %w", err)
	}
	if err := inst.systemd.Start(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("start service: %w", err)
	}
	return nil
}

func (inst *Installer) freshInstall(ctx context.Context, cfg *Config, imageRef string) error {
	if cfg.SSLCert != "" {
		if err := inst.copyUserTLS(cfg); err != nil {
			return fmt.Errorf("TLS certificate setup: %w", err)
		}
	}

	spec := system.QuadletSpec{
		Image:      imageRef,
		DataDir:    cfg.DataDir,
		Hostname:   cfg.Hostname,
		Port:       cfg.Port,
		ConfigPath: cfg.ConfigPath,
	}
	if err := inst.quadlet.Install(quadletServiceName, &spec); err != nil {
		return fmt.Errorf("install quadlet: %w", err)
	}
	slog.Info("quadlet installed", "path", inst.env.QuadletPath(quadletServiceName))

	if err := inst.systemd.DaemonReload(ctx); err != nil {
		return fmt.Errorf("reload systemd: %w", err)
	}
	if err := inst.systemd.Start(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("start service: %w", err)
	}

	if inst.env.Mode == system.UserMode {
		_ = inst.systemd.EnableLinger(ctx)
	}
	return nil
}

func (inst *Installer) waitForHealth(ctx context.Context, url, certPath string, skipHostname bool, timeout time.Duration) error {
	deadline := time.After(timeout)

	// Wait for the container to generate the TLS certificate.
	for {
		if _, err := inst.fs.Stat(certPath); err == nil {
			break
		}
		select {
		case <-deadline:
			return fmt.Errorf("timed out waiting for certificate: %s", certPath)
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(500 * time.Millisecond):
		}
	}

	caCert, err := inst.fs.ReadFile(certPath)
	if err != nil {
		return fmt.Errorf("read TLS certificate: %w", err)
	}
	tlsCfg, err := healthTLSConfig(caCert, skipHostname)
	if err != nil {
		return fmt.Errorf("parse TLS certificate %s: %w", certPath, err)
	}
	client := &http.Client{
		Timeout:   2 * time.Second,
		Transport: &http.Transport{TLSClientConfig: tlsCfg},
	}
	return system.WaitForHealth(ctx, client, url, timeout)
}

func healthTLSConfig(caCert []byte, skipHostname bool) (*tls.Config, error) {
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caCert) {
		return nil, fmt.Errorf("no certificates found")
	}

	tlsCfg := certs.SecureTLSConfig()
	tlsCfg.RootCAs = pool
	if skipHostname {
		cert, err := parseCertPEM(caCert)
		if err != nil {
			return nil, err
		}
		serverName, err := healthServerName(cert)
		if err != nil {
			return nil, err
		}
		// A non-empty ServerName prevents net/http from substituting the URL
		// hostname. Standard TLS verification remains enabled against an identity
		// declared by the installed certificate and the pinned certificate pool.
		tlsCfg.ServerName = serverName
	}
	return tlsCfg, nil
}

func healthServerName(cert *x509.Certificate) (string, error) {
	for _, dnsName := range cert.DNSNames {
		candidate := dnsName
		if strings.HasPrefix(candidate, "*.") {
			candidate = "health-check." + strings.TrimPrefix(candidate, "*.")
		}
		if err := cert.VerifyHostname(candidate); err == nil {
			return candidate, nil
		}
	}
	for _, ip := range cert.IPAddresses {
		candidate := ip.String()
		if err := cert.VerifyHostname(candidate); err == nil {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("certificate has no usable DNS or IP subject alternative name")
}

func validateInitConfig(cfg *Config) error {
	if err := ValidateInitUsername(cfg.InitUser); err != nil {
		return fmt.Errorf("invalid username %q: %w", cfg.InitUser, err)
	}
	if cfg.InitPasswordSet || cfg.InitPassword != "" {
		if err := ValidateInitPassword(cfg.InitPassword); err != nil {
			return fmt.Errorf("invalid password: %w", err)
		}
	}
	return nil
}

func (inst *Installer) initialize(ctx context.Context, cfg *Config) error {
	for _, dir := range []string{cfg.DataDir, filepath.Join(cfg.DataDir, "storage")} {
		if err := inst.fs.MkdirAll(dir, 0o750); err != nil {
			return fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

	dbPath, runtimeCfg, err := resolveInitDatabase(cfg)
	if err != nil {
		return err
	}

	db, err := dbcore.Setup(ctx, dbPath)
	if err != nil {
		return fmt.Errorf("database setup: %w", err)
	}
	defer func() { _ = db.Close() }()

	hasUsers, err := bootstrap.HasUsers(ctx, db)
	if err != nil {
		return err
	}
	if hasUsers {
		if cfg.InitPasswordSet || cfg.InitPassword != "" {
			return fmt.Errorf("registry is already initialized; supplied password was not applied and existing credentials are unchanged")
		}
		slog.Info("initial administrator already provisioned")
		return nil
	}

	if runtimeCfg != nil && !slices.Contains(runtimeCfg.SuperUsers, cfg.InitUser) {
		return fmt.Errorf("initial username %q is not listed in SUPER_USERS", cfg.InitUser)
	}

	password, err := inst.prepareInitialPassword(cfg)
	if err != nil {
		return err
	}
	created, err := bootstrap.AdminUser(ctx, db, cfg.InitUser, password)
	if err != nil {
		return fmt.Errorf("create initial administrator: %w", err)
	}
	if !created {
		return fmt.Errorf("initial administrator was created concurrently; credentials were not changed")
	}
	return nil
}

func resolveInitDatabase(cfg *Config) (string, *config.Config, error) {
	dbPath := filepath.Join(cfg.DataDir, "quay.db")
	if cfg.ConfigPath == "" {
		return dbPath, nil, nil
	}

	hostConfigPath, err := hostDataPath(cfg.DataDir, cfg.ConfigPath)
	if err != nil {
		return "", nil, fmt.Errorf("resolve config path: %w", err)
	}
	resolved, err := config.Resolve(hostConfigPath, cfg.DataDir, cfg.Hostname)
	if err != nil {
		return "", nil, fmt.Errorf("resolve config: %w", err)
	}
	dbPath, err = hostDataPath(cfg.DataDir, resolved.DBPath)
	if err != nil {
		return "", nil, fmt.Errorf("resolve database path: %w", err)
	}
	return dbPath, resolved.Config, nil
}

func hostDataPath(dataDir, path string) (string, error) {
	if path == "/data" {
		return dataDir, nil
	}
	if relative, ok := strings.CutPrefix(path, "/data/"); ok {
		cleaned := filepath.Clean(relative)
		if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
			return "", fmt.Errorf("path %q escapes /data", path)
		}
		return filepath.Join(dataDir, cleaned), nil
	}
	return path, nil
}

func (inst *Installer) prepareInitialPassword(cfg *Config) (string, error) {
	authDir := filepath.Join(cfg.DataDir, "auth")
	if err := inst.secureAuthDir(authDir); err != nil {
		return "", err
	}

	passwordPath := filepath.Join(authDir, "admin-password")
	info, err := inst.fs.Lstat(passwordPath)
	switch {
	case err == nil && !info.Mode().IsRegular():
		return "", fmt.Errorf("credential destination %s is not a regular file", passwordPath)
	case err != nil && !errors.Is(err, os.ErrNotExist):
		return "", fmt.Errorf("inspect credential destination: %w", err)
	}

	provided := cfg.InitPasswordSet || cfg.InitPassword != ""
	if err == nil && !provided {
		if info.Mode().Perm() != 0o600 {
			return "", fmt.Errorf("existing credential file %s has unsafe permissions %04o", passwordPath, info.Mode().Perm())
		}
		data, readErr := inst.fs.ReadFile(passwordPath)
		if readErr != nil {
			return "", fmt.Errorf("read existing credential file: %w", readErr)
		}
		password := string(data)
		if validateErr := ValidateInitPassword(password); validateErr != nil {
			return "", fmt.Errorf("existing credential file is invalid; retry with -init-password-stdin: %w", validateErr)
		}
		return password, nil
	}

	password := cfg.InitPassword
	if !provided {
		password = rand.Text()
	}
	if err := ValidateInitPassword(password); err != nil {
		return "", fmt.Errorf("invalid password: %w", err)
	}
	if err := inst.atomicWriteCredential(authDir, passwordPath, []byte(password)); err != nil {
		return "", err
	}
	return password, nil
}

func (inst *Installer) secureAuthDir(authDir string) error {
	info, err := inst.fs.Lstat(authDir)
	switch {
	case errors.Is(err, os.ErrNotExist):
		if err := inst.fs.MkdirAll(authDir, 0o700); err != nil {
			return fmt.Errorf("create auth directory: %w", err)
		}
	case err != nil:
		return fmt.Errorf("inspect auth directory: %w", err)
	case !info.IsDir():
		return fmt.Errorf("auth destination %s is not a directory", authDir)
	}
	if err := inst.fs.Chmod(authDir, 0o700); err != nil {
		return fmt.Errorf("secure auth directory: %w", err)
	}
	return nil
}

func (inst *Installer) atomicWriteCredential(dir, destination string, data []byte) (retErr error) {
	stagingDir, err := inst.fs.MkdirTemp(dir, ".credential-")
	if err != nil {
		return fmt.Errorf("create credential staging directory: %w", err)
	}
	stagedPath := filepath.Join(stagingDir, "admin-password")
	defer func() {
		if err := inst.fs.Remove(stagedPath); err != nil && !errors.Is(err, os.ErrNotExist) {
			retErr = errors.Join(retErr, fmt.Errorf("remove staged credential: %w", err))
		}
		if err := inst.fs.Remove(stagingDir); err != nil && !errors.Is(err, os.ErrNotExist) {
			retErr = errors.Join(retErr, fmt.Errorf("remove credential staging directory: %w", err))
		}
	}()
	if err := inst.fs.Chmod(stagingDir, 0o700); err != nil {
		return fmt.Errorf("secure credential staging directory: %w", err)
	}
	if err := inst.fs.WriteFile(stagedPath, data, 0o600); err != nil {
		return fmt.Errorf("stage credential: %w", err)
	}
	if err := inst.fs.Chmod(stagedPath, 0o600); err != nil {
		return fmt.Errorf("secure staged credential: %w", err)
	}
	if err := inst.fs.Rename(stagedPath, destination); err != nil {
		return fmt.Errorf("install credential: %w", err)
	}
	return nil
}

func (inst *Installer) dumpContainerLogs(ctx context.Context) {
	slog.Info("dumping container logs for diagnostics")
	_ = inst.runner.Run(ctx, "podman", "logs", quadletServiceName)
	_ = inst.runner.Run(ctx, "systemctl", "status", quadletServiceName)
}

// ValidateSSLFlags checks that -ssl-cert and -ssl-key are either both provided
// or both absent. Returns an error if only one is set.
func ValidateSSLFlags(sslCert, sslKey string) error {
	if (sslCert == "") != (sslKey == "") {
		return fmt.Errorf("-ssl-cert and -ssl-key must both be provided")
	}
	return nil
}

// copyUserTLS validates and copies user-provided TLS cert/key into the data
// directory so the serve process uses them instead of auto-generating.
func (inst *Installer) copyUserTLS(cfg *Config) error {
	certData, err := inst.fs.ReadFile(cfg.SSLCert)
	if err != nil {
		return fmt.Errorf("read certificate: %w", err)
	}
	keyData, err := inst.fs.ReadFile(cfg.SSLKey)
	if err != nil {
		return fmt.Errorf("read key: %w", err)
	}

	if _, err := tls.X509KeyPair(certData, keyData); err != nil {
		return fmt.Errorf("certificate/key pair invalid: %w", err)
	}

	if !cfg.SSLSkipHostnameVerification {
		cert, err := parseCertPEM(certData)
		if err != nil {
			return fmt.Errorf("parse certificate: %w", err)
		}
		if err := verifyCertHostname(cert, cfg.Hostname); err != nil {
			return fmt.Errorf("certificate hostname check failed (use -ssl-skip-hostname-verification to override): %w", err)
		}
	}

	if err := inst.replaceTLSFiles(cfg.DataDir, certData, keyData); err != nil {
		return err
	}

	certDst := filepath.Join(cfg.DataDir, "ssl.cert")
	keyDst := filepath.Join(cfg.DataDir, "ssl.key")
	slog.Info("user-provided TLS certificate installed", "cert", certDst, "key", keyDst)
	return nil
}

type tlsDestination struct {
	path       string
	backupPath string
	info       os.FileInfo
}

func (inst *Installer) replaceTLSFiles(dataDir string, certData, keyData []byte) (retErr error) {
	destinations := []tlsDestination{
		{path: filepath.Join(dataDir, "ssl.cert")},
		{path: filepath.Join(dataDir, "ssl.key")},
	}
	if err := inst.inspectTLSDestinations(destinations); err != nil {
		return err
	}

	stagingDir, err := inst.fs.MkdirTemp(dataDir, ".tls-update-")
	if err != nil {
		return fmt.Errorf("create TLS staging directory: %w", err)
	}

	stagedPaths := []string{
		filepath.Join(stagingDir, "ssl.cert"),
		filepath.Join(stagingDir, "ssl.key"),
	}
	cleanupPaths := append([]string(nil), stagedPaths...)
	defer func() {
		retErr = errors.Join(retErr, inst.cleanupTLSStaging(stagingDir, cleanupPaths))
	}()

	if err := inst.stageTLSFiles(stagedPaths, destinations, [][]byte{certData, keyData}); err != nil {
		return err
	}

	for i := range destinations {
		if destinations[i].info == nil {
			continue
		}
		destinations[i].backupPath = filepath.Join(stagingDir, filepath.Base(destinations[i].path)+".rollback")
		cleanupPaths = append(cleanupPaths, destinations[i].backupPath)
	}

	if err := inst.preserveTLSDestinations(destinations); err != nil {
		return err
	}
	return inst.commitTLSFiles(stagedPaths, destinations)
}

func (inst *Installer) inspectTLSDestinations(destinations []tlsDestination) error {
	for i := range destinations {
		info, _, err := inst.regularDestination(destinations[i].path)
		if err != nil {
			return err
		}
		destinations[i].info = info
	}
	return nil
}

func (inst *Installer) stageTLSFiles(stagedPaths []string, destinations []tlsDestination, contents [][]byte) error {
	for i, data := range contents {
		if err := inst.fs.WriteFile(stagedPaths[i], data, 0o600); err != nil {
			return fmt.Errorf("stage %s: %w", filepath.Base(destinations[i].path), err)
		}
		if err := inst.fs.Chmod(stagedPaths[i], 0o600); err != nil {
			return fmt.Errorf("secure staged %s: %w", filepath.Base(destinations[i].path), err)
		}
	}
	return nil
}

func (inst *Installer) preserveTLSDestinations(destinations []tlsDestination) error {
	for _, destination := range destinations {
		if destination.info == nil {
			continue
		}
		if err := inst.ensureDestinationUnchanged(destination); err != nil {
			return err
		}
		if err := inst.fs.Link(destination.path, destination.backupPath); err != nil {
			return fmt.Errorf("preserve existing %s: %w", filepath.Base(destination.path), err)
		}
	}
	return nil
}

func (inst *Installer) commitTLSFiles(stagedPaths []string, destinations []tlsDestination) error {
	replaced := false
	for i := range destinations {
		if err := inst.ensureDestinationUnchanged(destinations[i]); err != nil {
			if replaced {
				return errors.Join(err, inst.restoreTLSDestinations(destinations))
			}
			return err
		}
		if err := inst.fs.Rename(stagedPaths[i], destinations[i].path); err != nil {
			rollbackErr := inst.restoreTLSDestinations(destinations)
			return errors.Join(fmt.Errorf("replace %s: %w", filepath.Base(destinations[i].path), err), rollbackErr)
		}
		replaced = true
	}
	return nil
}

func (inst *Installer) cleanupTLSStaging(stagingDir string, paths []string) error {
	var cleanupErr error
	for _, path := range paths {
		if err := inst.fs.Remove(path); err != nil && !errors.Is(err, os.ErrNotExist) {
			cleanupErr = errors.Join(cleanupErr, fmt.Errorf("remove staged TLS file %s: %w", path, err))
		}
	}
	if err := inst.fs.Remove(stagingDir); err != nil && !errors.Is(err, os.ErrNotExist) {
		cleanupErr = errors.Join(cleanupErr, fmt.Errorf("remove TLS staging directory: %w", err))
	}
	return cleanupErr
}

func (inst *Installer) regularDestination(path string) (info os.FileInfo, exists bool, err error) {
	info, err = inst.fs.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, fmt.Errorf("inspect TLS destination %s: %w", path, err)
	}
	if !info.Mode().IsRegular() {
		return nil, false, fmt.Errorf("TLS destination %s is not a regular file", path)
	}
	return info, true, nil
}

func (inst *Installer) ensureDestinationUnchanged(destination tlsDestination) error {
	info, exists, err := inst.regularDestination(destination.path)
	if err != nil {
		return err
	}
	if destination.info == nil {
		if exists {
			return fmt.Errorf("TLS destination %s appeared during replacement", destination.path)
		}
		return nil
	}
	if !exists || !os.SameFile(destination.info, info) {
		return fmt.Errorf("TLS destination %s changed during replacement", destination.path)
	}
	return nil
}

func (inst *Installer) restoreTLSDestinations(destinations []tlsDestination) error {
	var rollbackErr error
	for _, destination := range destinations {
		if destination.info == nil {
			if err := inst.fs.Remove(destination.path); err != nil && !errors.Is(err, os.ErrNotExist) {
				rollbackErr = errors.Join(rollbackErr, fmt.Errorf("remove partial %s: %w", destination.path, err))
			}
			continue
		}
		if err := inst.fs.Rename(destination.backupPath, destination.path); err != nil {
			rollbackErr = errors.Join(rollbackErr, fmt.Errorf("restore %s: %w", destination.path, err))
		}
	}
	if rollbackErr != nil {
		return fmt.Errorf("rollback TLS replacement: %w", rollbackErr)
	}
	return nil
}

func parseCertPEM(data []byte) (*x509.Certificate, error) {
	var block *pem.Block
	rest := data
	for {
		block, rest = pem.Decode(rest)
		if block == nil {
			return nil, fmt.Errorf("no CERTIFICATE block found in PEM data")
		}
		if block.Type == "CERTIFICATE" {
			break
		}
	}
	return x509.ParseCertificate(block.Bytes)
}

func verifyCertHostname(cert *x509.Certificate, hostname string) error {
	if ip := net.ParseIP(hostname); ip != nil {
		for _, certIP := range cert.IPAddresses {
			if certIP.Equal(ip) {
				return nil
			}
		}
		return fmt.Errorf("certificate does not contain IP SAN for %s", hostname)
	}
	if err := cert.VerifyHostname(hostname); err != nil {
		return fmt.Errorf("hostname %q not in certificate SANs: %w", hostname, err)
	}
	return nil
}
