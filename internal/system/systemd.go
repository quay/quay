package system

import "context"

// ServiceManager abstracts systemd service operations.
type ServiceManager interface {
	DaemonReload(ctx context.Context) error
	Enable(ctx context.Context, service string) error
	Start(ctx context.Context, service string) error
	Stop(ctx context.Context, service string) error
	EnableLinger(ctx context.Context) error
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

// Enable enables and starts a systemd service.
func (s *SystemdManager) Enable(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "enable", "--now", service)...)
}

// Start starts a systemd service.
func (s *SystemdManager) Start(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "start", service)...)
}

// Stop stops a systemd service.
func (s *SystemdManager) Stop(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "stop", service)...)
}

// EnableLinger enables lingering for the current user in user mode.
func (s *SystemdManager) EnableLinger(ctx context.Context) error {
	if s.env.Mode == RootMode || s.env.Username == "" {
		return nil
	}
	return s.runner.Run(ctx, "loginctl", "enable-linger", s.env.Username)
}
