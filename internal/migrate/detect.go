package migrate

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// OMR service names.
var omrServiceNames = []string{"quay-app", "quay-redis", "quay-pod"}

// detectSystemd scans for old OMR systemd unit files and extracts paths.
func (m *Migrator) detectSystemd(ctx context.Context) (OMRSource, error) {
	for _, scope := range []struct {
		name string
		dirs []string
	}{
		{scopeSystem, []string{"/etc/systemd/system"}},
		{scopeUser, userSystemdDirs()},
	} {
		for _, dir := range scope.dirs {
			unitPath := filepath.Join(dir, "quay-app.service")
			data, err := os.ReadFile(unitPath) //nolint:gosec // well-known systemd path
			if err != nil {
				continue
			}
			slog.Info("found OMR unit file", "path", unitPath)
			return m.sourceFromUnit(ctx, string(data), scope.name, dir)
		}
	}
	return OMRSource{}, fmt.Errorf("no OMR systemd units found")
}

func userSystemdDirs() []string {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil
	}
	return []string{filepath.Join(home, ".config", "systemd", "user")}
}

func (m *Migrator) sourceFromUnit(ctx context.Context, unitContent, scope, unitDir string) (OMRSource, error) {
	vols := parseUnitVolumes(unitContent)

	src := OMRSource{
		SystemdScope: scope,
		Method:       "systemd",
	}

	// Collect unit file paths for cleanup.
	for _, svc := range omrServiceNames {
		p := filepath.Join(unitDir, svc+".service")
		if _, err := os.Stat(p); err == nil {
			src.UnitFiles = append(src.UnitFiles, p)
		}
	}

	// Extract config dir from the /quay-registry/conf/stack mount.
	if hostPath, ok := vols["/quay-registry/conf/stack"]; ok {
		src.ConfigDir = hostPath
	}

	// Extract sqlite storage from /sqlite mount.
	if hostPath, ok := vols["/sqlite"]; ok {
		resolved, volName, err := m.resolveVolumePath(ctx, hostPath)
		if err == nil {
			src.DBPath = filepath.Join(resolved, "quay_sqlite.db")
			if volName != "" {
				src.VolumeNames = append(src.VolumeNames, volName)
			}
		}
	}

	// Extract blob storage from /datastorage mount.
	if hostPath, ok := vols["/datastorage"]; ok {
		resolved, volName, err := m.resolveVolumePath(ctx, hostPath)
		if err == nil {
			src.StoragePath = resolved
			if volName != "" {
				src.VolumeNames = append(src.VolumeNames, volName)
			}
		}
	}

	// Extract hostname from config.yaml.
	if src.ConfigDir != "" {
		configPath := filepath.Join(src.ConfigDir, "config.yaml")
		data, err := os.ReadFile(configPath) //nolint:gosec // detected config path
		if err == nil {
			hostname, err := extractHostname(data)
			if err == nil {
				src.Hostname = hostname
			}
		}
	}

	return src, nil
}

// parseUnitVolumes extracts -v host:container[:opts] mappings from a systemd unit.
// Returns map[containerPath]hostPath.
func parseUnitVolumes(unitContent string) map[string]string {
	vols := make(map[string]string)
	// Join continuation lines (backslash-newline).
	joined := strings.ReplaceAll(unitContent, "\\\n", " ")
	for _, line := range strings.Split(joined, "\n") {
		line = strings.TrimSpace(line)
		parts := strings.Fields(line)
		for i, p := range parts {
			if p == "-v" && i+1 < len(parts) {
				mountSpec := parts[i+1]
				colonParts := strings.SplitN(mountSpec, ":", 3)
				if len(colonParts) >= 2 {
					vols[colonParts[1]] = colonParts[0]
				}
			}
		}
	}
	return vols
}

// resolveVolumePath resolves a volume mount source. If it starts with /,
// it's a host path (returned as-is). Otherwise it's a Podman volume name
// and we inspect it to get the mountpoint.
func (m *Migrator) resolveVolumePath(ctx context.Context, hostOrVolume string) (path, volumeName string, err error) {
	if filepath.IsAbs(hostOrVolume) {
		return hostOrVolume, "", nil
	}
	if m.Runner == nil {
		return "", "", fmt.Errorf("no command runner for volume inspection")
	}
	output, err := m.Runner.Output(ctx, "podman", "volume", "inspect", hostOrVolume, "--format", "{{.Mountpoint}}")
	if err != nil {
		return "", "", fmt.Errorf("inspect volume %s: %w", hostOrVolume, err)
	}
	return strings.TrimSpace(output), hostOrVolume, nil
}

// detectPodmanVolumes probes for well-known OMR volume names.
func (m *Migrator) detectPodmanVolumes(ctx context.Context) (OMRSource, error) {
	if m.Runner == nil {
		return OMRSource{}, fmt.Errorf("no command runner")
	}
	src := OMRSource{Method: "podman-volume"}
	sqlitePath, volName, err := m.resolveVolumePath(ctx, "sqlite-storage")
	if err != nil {
		return OMRSource{}, fmt.Errorf("sqlite-storage volume: %w", err)
	}
	src.DBPath = filepath.Join(sqlitePath, "quay_sqlite.db")
	src.VolumeNames = append(src.VolumeNames, volName)

	storagePath, volName, err := m.resolveVolumePath(ctx, "quay-storage")
	if err != nil {
		return OMRSource{}, fmt.Errorf("quay-storage volume: %w", err)
	}
	src.StoragePath = storagePath
	src.VolumeNames = append(src.VolumeNames, volName)

	// Try well-known config dir.
	home, _ := os.UserHomeDir()
	if home != "" {
		configDir := filepath.Join(home, "quay-install", "quay-config")
		if _, err := os.Stat(configDir); err == nil {
			src.ConfigDir = configDir
		}
	}

	// Extract hostname if config found.
	if src.ConfigDir != "" {
		data, err := os.ReadFile(filepath.Join(src.ConfigDir, "config.yaml")) //nolint:gosec // detected config path
		if err == nil {
			hostname, _ := extractHostname(data)
			src.Hostname = hostname
		}
	}

	return src, nil
}

// detectDefaults uses well-known paths without querying podman or systemd.
func (m *Migrator) detectDefaults() (OMRSource, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return OMRSource{}, fmt.Errorf("home dir: %w", err)
	}
	root := filepath.Join(home, "quay-install")
	if m.SourceRoot != "" {
		root = m.SourceRoot
	}
	configDir := filepath.Join(root, "quay-config")
	if _, err := os.Stat(configDir); err != nil {
		return OMRSource{}, fmt.Errorf("config dir %s not found: %w", configDir, err)
	}
	src := OMRSource{
		ConfigDir:   configDir,
		DBPath:      filepath.Join(root, "sqlite-storage", "quay_sqlite.db"),
		StoragePath: filepath.Join(root, "quay-storage"),
		Method:      "defaults",
	}
	data, err := os.ReadFile(filepath.Join(configDir, "config.yaml")) //nolint:gosec // detected config path
	if err == nil {
		hostname, _ := extractHostname(data)
		src.Hostname = hostname
	}
	return src, nil
}

// detect tries each strategy in order.
func (m *Migrator) detect(ctx context.Context) (OMRSource, error) {
	if src, err := m.detectSystemd(ctx); err == nil {
		slog.Info("detected OMR via systemd units", "scope", src.SystemdScope)
		return m.withImageArchive(&src), nil
	}
	if src, err := m.detectPodmanVolumes(ctx); err == nil {
		slog.Info("detected OMR via podman volumes")
		return m.withImageArchive(&src), nil
	}
	src, err := m.detectDefaults()
	if err != nil {
		return OMRSource{}, fmt.Errorf("could not detect OMR installation: %w", err)
	}
	slog.Info("detected OMR via default paths")
	return m.withImageArchive(&src), nil
}

func (m *Migrator) withImageArchive(src *OMRSource) OMRSource {
	if src.ImageArchive != "" || m.ImageArchive != "" {
		return *src
	}
	exe, err := os.Executable()
	if err != nil {
		return *src
	}
	archive, err := findImageArchive(filepath.Dir(exe))
	if err == nil {
		src.ImageArchive = archive
		slog.Info("auto-detected image archive", "path", archive)
	}
	return *src
}

// extractHostname parses SERVER_HOSTNAME from an OMR config.yaml.
// Strips any port suffix since the installer adds :8443 itself.
func extractHostname(data []byte) (string, error) {
	var raw map[string]any
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return "", fmt.Errorf("parse config: %w", err)
	}
	hostname, ok := raw["SERVER_HOSTNAME"].(string)
	if !ok || hostname == "" {
		return "", fmt.Errorf("SERVER_HOSTNAME not found in config")
	}
	if host, _, err := net.SplitHostPort(hostname); err == nil {
		hostname = host
	}
	return hostname, nil
}

// findImageArchive looks for a single .tar file in dir.
func findImageArchive(dir string) (string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return "", err
	}
	var tars []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".tar") {
			tars = append(tars, filepath.Join(dir, e.Name()))
		}
	}
	switch len(tars) {
	case 0:
		return "", fmt.Errorf("no .tar files found in %s", dir)
	case 1:
		return tars[0], nil
	default:
		return "", fmt.Errorf("multiple .tar files in %s; specify -image-archive explicitly", dir)
	}
}
