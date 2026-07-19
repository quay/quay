// Package installer implements the install and upgrade workflow for the
// registry's Quadlet-based systemd deployment.
package installer

import (
	"context"
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
	"strings"
	"time"

	"github.com/quay/quay/internal/certs"
	"github.com/quay/quay/internal/system"
)

const (
	// DefaultImage is the default container image for the registry.
	DefaultImage = "quay.io/quay/quay-mirror:latest"

	defaultPort        = "8443"
	quadletServiceName = "quay"
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

// Run performs an install or upgrade based on whether a Quadlet unit already
// exists.
func (inst *Installer) Run(ctx context.Context, cfg *Config) error {
	if cfg == nil {
		return fmt.Errorf("nil installer config")
	}

	upgrading := inst.quadlet.Exists(quadletServiceName)
	port, err := inst.resolvePort(cfg.Port, upgrading)
	if err != nil {
		return fmt.Errorf("resolve port: %w", err)
	}
	resolvedCfg := *cfg
	resolvedCfg.Port = port

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

	credPath := filepath.Join(resolvedCfg.DataDir, "credentials")
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
	for _, dir := range []string{cfg.DataDir, filepath.Join(cfg.DataDir, "storage")} {
		if err := inst.fs.MkdirAll(dir, 0o750); err != nil {
			return fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

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
