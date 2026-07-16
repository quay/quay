package system

import (
	"bufio"
	"fmt"
	"strings"
)

const registryContainerPort = "8443"

// QuadletSpec describes a Quadlet container unit.
type QuadletSpec struct {
	Image         string
	DataDir       string
	Hostname      string
	Port          string
	ConfigPath    string
	AdminUsername string
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

	serveCommand := fmt.Sprintf("serve --data-dir /data --hostname %s", spec.Hostname)
	if spec.ConfigPath != "" {
		serveCommand = fmt.Sprintf("serve --config %s", spec.ConfigPath)
	}
	if spec.AdminUsername != "" && spec.AdminUsername != "admin" {
		serveCommand += fmt.Sprintf(" --admin-username %s", spec.AdminUsername)
	}

	content := fmt.Sprintf(`[Unit]
Description=Quay OCI Registry
After=network-online.target

[Container]
Image=%s
Volume=%s:/data:Z
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

	return q.fs.WriteFile(path, []byte(strings.Join(updated, "\n")+"\n"), 0o600)
}
