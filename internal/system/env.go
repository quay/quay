package system

import (
	"fmt"
	"os"
	"os/user"
	"path/filepath"
)

// Mode distinguishes root vs user-level installation.
type Mode int

// Installation modes.
const (
	RootMode Mode = iota
	UserMode
)

// Env captures the execution environment, resolved once at startup.
type Env struct {
	Mode     Mode
	HomeDir  string
	Username string
}

// NewEnv detects root/user mode and resolves paths.
func NewEnv() (*Env, error) {
	if os.Getuid() == 0 {
		return &Env{Mode: RootMode}, nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("determine home directory: %w", err)
	}
	u, err := user.Current()
	if err != nil {
		return nil, fmt.Errorf("determine current user: %w", err)
	}
	return &Env{
		Mode:     UserMode,
		HomeDir:  home,
		Username: u.Username,
	}, nil
}

// QuadletDir returns the systemd Quadlet directory for this mode.
func (e *Env) QuadletDir() string {
	if e.Mode == RootMode {
		return "/etc/containers/systemd"
	}
	return filepath.Join(e.HomeDir, ".config", "containers", "systemd")
}

// QuadletPath returns the full path to a Quadlet .container file.
func (e *Env) QuadletPath(service string) string {
	return filepath.Join(e.QuadletDir(), service+".container")
}

// SystemctlArgs returns the extra args needed for systemctl in this mode.
func (e *Env) SystemctlArgs() []string {
	if e.Mode == RootMode {
		return nil
	}
	return []string{"--user"}
}
