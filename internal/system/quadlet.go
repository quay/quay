package system

import (
	"bufio"
	"fmt"
	"strings"
)

// QuadletSpec describes a Quadlet container unit.
type QuadletSpec struct {
	Image    string
	DataDir  string
	Hostname string
	Port     string
}

// QuadletManager handles Quadlet .container files.
type QuadletManager struct {
	FS  FileSystem
	Env *Env
}

// Exists returns true if the Quadlet file for service already exists.
func (q *QuadletManager) Exists(service string) bool {
	_, err := q.FS.Stat(q.Env.QuadletPath(service))
	return err == nil
}

// Install writes a new Quadlet .container file.
func (q *QuadletManager) Install(service string, spec QuadletSpec) error {
	dir := q.Env.QuadletDir()
	if err := q.FS.MkdirAll(dir, 0o750); err != nil {
		return fmt.Errorf("create quadlet dir: %w", err)
	}

	content := fmt.Sprintf(`[Unit]
Description=Quay OCI Registry
After=network-online.target

[Container]
Image=%s
Volume=%s:/data:Z
PublishPort=%s:%s
Exec=serve --data-dir /data --hostname %s

[Install]
WantedBy=default.target
`, spec.Image, spec.DataDir, spec.Port, spec.Port, spec.Hostname)

	path := q.Env.QuadletPath(service)
	if err := q.FS.WriteFile(path, []byte(content), 0o600); err != nil {
		return fmt.Errorf("write quadlet: %w", err)
	}
	return nil
}

// UpdateImage replaces the Image= directive in an existing Quadlet file.
func (q *QuadletManager) UpdateImage(service, newImage string) error {
	path := q.Env.QuadletPath(service)
	data, err := q.FS.ReadFile(path)
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
		return fmt.Errorf("no Image= directive found in %s", path)
	}

	return q.FS.WriteFile(path, []byte(strings.Join(updated, "\n")+"\n"), 0o600)
}
