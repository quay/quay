package migrate

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// OMR service names.
var omrServiceNames = []string{"quay-app", "quay-redis", "quay-pod"}

const (
	postgresContainerName = "quay-postgres"
	podName               = "quay-pod"
)

var errNoSystemdUnits = errors.New("no OMR systemd units found")

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
	return OMRSource{}, errNoSystemdUnits
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

	// OMR has used both config mount destinations.
	if m.Source.ConfigDir != "" {
		src.ConfigDir = m.Source.ConfigDir
	} else if hostPath, ok := vols["/quay-registry/conf/stack"]; ok {
		src.ConfigDir = hostPath
	} else if hostPath, ok := vols["/conf/stack"]; ok {
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

	if err := m.populateSourceConfig(ctx, &src, unitDir); err != nil {
		return OMRSource{}, err
	}
	return src, nil
}

func (m *Migrator) populateSourceConfig(ctx context.Context, src *OMRSource, unitDir string) error {
	if src.ConfigDir != "" {
		data, err := os.ReadFile(filepath.Join(src.ConfigDir, "config.yaml")) //nolint:gosec // detected config path
		if err == nil {
			src.DatabaseKind, err = extractDatabaseKind(data)
			if err != nil {
				return err
			}
			src.Hostname, src.Port, _ = extractHostname(data)
		}
		src.RootCADir = detectRootCADir(src.ConfigDir)
	}
	if src.DatabaseKind == "" {
		src.DatabaseKind = databaseSQLite
	}
	if src.DatabaseKind != databasePostgres {
		return nil
	}
	src.DBPath = ""
	sandboxKey, err := m.detectPostgresTopology(ctx, unitDir)
	if err != nil {
		return err
	}
	src.PodSandboxKey = sandboxKey
	return nil
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
	src := OMRSource{DatabaseKind: databaseSQLite, Method: "podman-volume"}
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

	// Extract hostname and port if config found.
	if src.ConfigDir != "" {
		data, err := os.ReadFile(filepath.Join(src.ConfigDir, "config.yaml")) //nolint:gosec // detected config path
		if err == nil {
			hostname, port, _ := extractHostname(data)
			src.Hostname = hostname
			src.Port = port
		}
		src.RootCADir = detectRootCADir(src.ConfigDir)
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
		DatabaseKind: databaseSQLite,
		ConfigDir:    configDir,
		DBPath:       filepath.Join(root, "sqlite-storage", "quay_sqlite.db"),
		StoragePath:  filepath.Join(root, "quay-storage"),
		Method:       "defaults",
	}
	data, err := os.ReadFile(filepath.Join(configDir, "config.yaml")) //nolint:gosec // detected config path
	if err == nil {
		hostname, port, _ := extractHostname(data)
		src.Hostname = hostname
		src.Port = port
	}
	src.RootCADir = detectRootCADir(configDir)
	return src, nil
}

// detect tries each strategy in order.
func (m *Migrator) detect(ctx context.Context) (OMRSource, error) {
	src, err := m.detectSystemd(ctx)
	if err == nil {
		slog.Info("detected OMR via systemd units", "scope", src.SystemdScope)
		return m.withImageArchive(&src), nil
	}
	if !errors.Is(err, errNoSystemdUnits) {
		return OMRSource{}, fmt.Errorf("detect OMR from systemd: %w", err)
	}
	if src, err := m.detectPodmanVolumes(ctx); err == nil {
		slog.Info("detected OMR via podman volumes")
		return m.withImageArchive(&src), nil
	}
	src, err = m.detectDefaults()
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

func extractDatabaseKind(data []byte) (string, error) {
	var raw struct {
		DBURI string `yaml:"DB_URI"`
	}
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return "", fmt.Errorf("parse config: %w", err)
	}
	u, err := url.Parse(raw.DBURI)
	if err != nil {
		return "", fmt.Errorf("parse DB_URI: %w", err)
	}
	switch u.Scheme {
	case "sqlite":
		return databaseSQLite, nil
	case "postgresql":
		if _, err := parsePostgresURI(raw.DBURI); err != nil {
			return "", err
		}
		return databasePostgres, nil
	default:
		return "", fmt.Errorf("unsupported DB_URI scheme %q", u.Scheme)
	}
}

func parsePostgresURI(raw string) (*url.URL, error) {
	u, err := url.Parse(raw)
	if err != nil {
		return nil, fmt.Errorf("parse DB_URI: %w", err)
	}
	if u.Scheme != "postgresql" {
		return nil, fmt.Errorf("DB_URI scheme must be %q, got %q", "postgresql", u.Scheme)
	}
	if u.User == nil || u.User.Username() == "" {
		return nil, fmt.Errorf("DB_URI is missing username")
	}
	if _, ok := u.User.Password(); !ok {
		return nil, fmt.Errorf("DB_URI is missing password")
	}
	if u.Hostname() != postgresContainerName {
		return nil, fmt.Errorf("DB_URI host must be %q, got %q", postgresContainerName, u.Hostname())
	}
	if u.Port() != "" && u.Port() != "5432" {
		return nil, fmt.Errorf("DB_URI port must be 5432, got %q", u.Port())
	}
	if u.Path != "/quay" {
		return nil, fmt.Errorf("DB_URI database path must be %q, got %q", "/quay", u.Path)
	}
	if u.RawQuery != "" {
		return nil, fmt.Errorf("DB_URI contains unsupported query parameters")
	}
	if u.Fragment != "" {
		return nil, fmt.Errorf("DB_URI contains unsupported fragment")
	}
	return u, nil
}

func (m *Migrator) detectPostgresTopology(ctx context.Context, unitDir string) (string, error) {
	for _, service := range []string{postgresContainerName, podName} {
		if _, err := os.Stat(filepath.Join(unitDir, service+".service")); err != nil {
			return "", fmt.Errorf("read %s service: %w", service, err)
		}
	}
	if m.Runner == nil {
		return "", fmt.Errorf("no command runner for PostgreSQL topology detection")
	}

	containerOutput, err := m.Runner.Output(ctx, "podman", "inspect", postgresContainerName, "--format", "{{.Pod}} {{.NetworkSettings.SandboxKey}}")
	if err != nil {
		return "", fmt.Errorf("inspect %s container: %w", postgresContainerName, err)
	}
	podID, err := m.Runner.Output(ctx, "podman", "pod", "inspect", podName, "--format", "{{.Id}}")
	if err != nil {
		return "", fmt.Errorf("inspect %s pod: %w", podName, err)
	}
	appPodID, err := m.Runner.Output(ctx, "podman", "inspect", sourceContainerName, "--format", "{{.Pod}}")
	if err != nil {
		return "", fmt.Errorf("inspect %s container: %w", sourceContainerName, err)
	}
	if appPodID != podID {
		return "", fmt.Errorf("%s container is not in %s", sourceContainerName, podName)
	}
	containerFields := strings.Fields(containerOutput)
	if len(containerFields) == 0 || containerFields[0] != podID {
		return "", fmt.Errorf("%s container is not in %s", postgresContainerName, podName)
	}
	if len(containerFields) != 2 {
		return "", fmt.Errorf("%s network namespace has no sandbox key", podName)
	}
	return containerFields[1], nil
}

// extractHostname parses SERVER_HOSTNAME from an OMR config.yaml,
// returning the bare hostname and the port separately. If the value
// has no explicit port, port is returned as "".
func extractHostname(data []byte) (hostname, port string, _ error) {
	var raw map[string]any
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return "", "", fmt.Errorf("parse config: %w", err)
	}
	hostname, ok := raw["SERVER_HOSTNAME"].(string)
	if !ok || hostname == "" {
		return "", "", fmt.Errorf("SERVER_HOSTNAME not found in config")
	}
	if host, p, err := net.SplitHostPort(hostname); err == nil {
		return host, p, nil
	}
	return hostname, "", nil
}

// detectRootCADir checks for a quay-rootCA directory containing rootCA.pem
// as a sibling of the config directory (i.e. under the same quay-install root).
func detectRootCADir(configDir string) string {
	parent := filepath.Dir(configDir)
	caDir := filepath.Join(parent, "quay-rootCA")
	if _, err := os.Stat(filepath.Join(caDir, "rootCA.pem")); err == nil {
		return caDir
	}
	return ""
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
