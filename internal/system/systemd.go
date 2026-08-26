package system

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
)

// ErrUnitNotFound is returned when a systemd unit does not exist.
var ErrUnitNotFound = errors.New("systemd unit not found")

// ServiceManager abstracts systemd service operations.
type ServiceManager interface {
	DaemonReload(ctx context.Context) error
	Start(ctx context.Context, service string) error
	Stop(ctx context.Context, service string) error
	EnableLinger(ctx context.Context) error
	DisableLinger(ctx context.Context) error
}

// SystemdManager implements ServiceManager using systemctl.
type SystemdManager struct {
	runner CommandRunner
	env    *Env
}

// NewSystemdManager returns a SystemdManager backed by runner and env.
func NewSystemdManager(runner CommandRunner, env *Env) *SystemdManager {
	return &SystemdManager{runner: runner, env: env}
}

// DaemonReload runs systemctl daemon-reload.
func (s *SystemdManager) DaemonReload(ctx context.Context) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "daemon-reload")...)
}

// Start starts a systemd service.
func (s *SystemdManager) Start(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "start", service)...)
}

// Stop stops a systemd service. Returns ErrUnitNotFound if the unit does not
// exist (systemctl exit code 5).
func (s *SystemdManager) Stop(ctx context.Context, service string) error {
	err := s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "stop", service)...)
	if err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) && exitErr.ExitCode() == 5 {
			return fmt.Errorf("%w: %s", ErrUnitNotFound, service)
		}
	}
	return err
}

// EnableLinger enables lingering for the current user in user mode.
func (s *SystemdManager) EnableLinger(ctx context.Context) error {
	if s.env.Mode == RootMode || s.env.Username == "" {
		return nil
	}
	return s.runner.Run(ctx, "loginctl", "enable-linger", s.env.Username)
}

// DisableLinger disables lingering for the current user in user mode.
func (s *SystemdManager) DisableLinger(ctx context.Context) error {
	if s.env.Mode == RootMode || s.env.Username == "" {
		return nil
	}
	return s.runner.Run(ctx, "loginctl", "disable-linger", s.env.Username)
}
