package system

import (
	"bufio"
	"fmt"
	"net"
	"strings"
)

const registryContainerPort = "8443"

// QuadletSpec describes a Quadlet container unit.
type QuadletSpec struct {
	Image      string
	DataDir    string
	Hostname   string
	Port       string
	ConfigPath string
}

// QuadletManager handles Quadlet .container files.
type QuadletManager struct {
	fs  FileSystem
	env *Env
}

// NewQuadletManager returns a QuadletManager backed by fs and env.
func NewQuadletManager(fs FileSystem, env *Env) *QuadletManager {
	return &QuadletManager{fs: fs, env: env}
}

// Exists returns true if the Quadlet file for service already exists.
func (q *QuadletManager) Exists(service string) bool {
	_, err := q.fs.Stat(q.env.QuadletPath(service))
	return err == nil
}

// Install writes a new Quadlet .container file.
func (q *QuadletManager) Install(service string, spec *QuadletSpec) error {
	dir := q.env.QuadletDir()
	if err := q.fs.MkdirAll(dir, 0o750); err != nil {
		return fmt.Errorf("create quadlet dir: %w", err)
	}
	if spec == nil {
		return fmt.Errorf("nil quadlet spec")
	}

	serveCommand := quadletServeCommand(spec)

	content := fmt.Sprintf(`[Unit]
Description=Quay OCI Registry
After=network-online.target

[Container]
Image=%s
Volume=%s:/data:Z,U
PublishPort=%s:%s
Exec=%s

[Install]
WantedBy=default.target
`, spec.Image, spec.DataDir, spec.Port, registryContainerPort, serveCommand)

	path := q.env.QuadletPath(service)
	if err := q.fs.WriteFile(path, []byte(content), 0o600); err != nil {
		return fmt.Errorf("write quadlet: %w", err)
	}
	return nil
}

func quadletServeCommand(spec *QuadletSpec) string {
	publicHostname := net.JoinHostPort(strings.Trim(spec.Hostname, "[]"), spec.Port)
	if spec.ConfigPath != "" {
		return fmt.Sprintf("serve --config %s --hostname %s", spec.ConfigPath, publicHostname)
	}
	return fmt.Sprintf("serve --data-dir /data --hostname %s", publicHostname)
}

// HostPort returns the host port published by an existing Quadlet file.
func (q *QuadletManager) HostPort(service string) (string, error) {
	path := q.env.QuadletPath(service)
	data, err := q.fs.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read quadlet: %w", err)
	}

	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		mapping, found := strings.CutPrefix(scanner.Text(), "PublishPort=")
		if !found {
			continue
		}
		hostPort, _, found := strings.Cut(mapping, ":")
		if !found || hostPort == "" {
			return "", fmt.Errorf("invalid PublishPort= directive in %s", path)
		}
		return hostPort, nil
	}
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("scan quadlet: %w", err)
	}
	return "", fmt.Errorf("no PublishPort= directive found in %s", path)
}

// Hostname returns the hostname passed to serve by an existing Quadlet file.
func (q *QuadletManager) Hostname(service string) (string, error) {
	path := q.env.QuadletPath(service)
	data, err := q.fs.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read quadlet: %w", err)
	}

	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		command, found := strings.CutPrefix(scanner.Text(), "Exec=")
		if !found {
			continue
		}
		fields := strings.Fields(command)
		for i, field := range fields {
			if field != "--hostname" {
				continue
			}
			if i+1 >= len(fields) || fields[i+1] == "" {
				return "", fmt.Errorf("invalid hostname flag in Exec= directive in %s", path)
			}
			hostname, err := HostnameWithoutPort(fields[i+1])
			if err != nil {
				return "", fmt.Errorf("invalid hostname flag in Exec= directive in %s: %w", path, err)
			}
			return hostname, nil
		}
	}
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("scan quadlet: %w", err)
	}
	return "", fmt.Errorf("no hostname flag found in Exec= directive in %s", path)
}

// ConfigPath returns the configuration path passed to serve, or an empty
// string when the existing Quadlet uses command-line defaults.
func (q *QuadletManager) ConfigPath(service string) (string, error) {
	path := q.env.QuadletPath(service)
	data, err := q.fs.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read quadlet: %w", err)
	}

	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		command, found := strings.CutPrefix(scanner.Text(), "Exec=")
		if !found {
			continue
		}
		fields := strings.Fields(command)
		for i, field := range fields {
			if field != "--config" {
				continue
			}
			if i+1 >= len(fields) || fields[i+1] == "" {
				return "", fmt.Errorf("invalid config flag in Exec= directive in %s", path)
			}
			return fields[i+1], nil
		}
		return "", nil
	}
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("scan quadlet: %w", err)
	}
	return "", fmt.Errorf("no Exec= directive found in %s", path)
}

// UpdateImage replaces the image while retaining the existing published host port.
func (q *QuadletManager) UpdateImage(service, newImage string) error {
	hostPort, err := q.HostPort(service)
	if err != nil {
		return err
	}
	return q.UpdateImageAndPort(service, newImage, hostPort)
}

// UpdateImageAndPort replaces the image and published host port in an existing Quadlet file.
func (q *QuadletManager) UpdateImageAndPort(service, newImage, hostPort string) error {
	path := q.env.QuadletPath(service)
	data, err := q.fs.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read quadlet: %w", err)
	}

	var updated []string
	foundImage := false
	foundPort := false
	foundHostname := false
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	for scanner.Scan() {
		line := scanner.Text()
		switch {
		case strings.HasPrefix(line, "Image="):
			updated = append(updated, "Image="+newImage)
			foundImage = true
		case strings.HasPrefix(line, "PublishPort="):
			updated = append(updated, "PublishPort="+hostPort+":"+registryContainerPort)
			foundPort = true
		case strings.HasPrefix(line, "Exec="):
			command, found, err := updateServeHostname(strings.TrimPrefix(line, "Exec="), hostPort)
			if err != nil {
				return fmt.Errorf("update quadlet: %w", err)
			}
			updated = append(updated, "Exec="+command)
			foundHostname = foundHostname || found
		default:
			updated = append(updated, line)
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("scan quadlet: %w", err)
	}
	if !foundImage {
		return fmt.Errorf("no Image= directive found in %s", path)
	}
	if !foundPort {
		return fmt.Errorf("no PublishPort= directive found in %s", path)
	}
	if !foundHostname {
		return fmt.Errorf("no hostname flag found in Exec= directive in %s", path)
	}
	return q.fs.WriteFile(path, []byte(strings.Join(updated, "\n")+"\n"), 0o600)
}

func updateServeHostname(command, hostPort string) (updated string, found bool, updateErr error) {
	fields := strings.Fields(command)
	for i, field := range fields {
		if field != "--hostname" {
			continue
		}
		if i+1 >= len(fields) || fields[i+1] == "" {
			return "", false, fmt.Errorf("invalid hostname flag in Exec= directive")
		}
		hostname, err := HostnameWithoutPort(fields[i+1])
		if err != nil {
			return "", false, fmt.Errorf("invalid hostname flag in Exec= directive: %w", err)
		}
		fields[i+1] = net.JoinHostPort(hostname, hostPort)
		return strings.Join(fields, " "), true, nil
	}
	return command, false, nil
}
