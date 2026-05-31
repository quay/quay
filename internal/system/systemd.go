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

func NewSystemdManager(runner CommandRunner, env *Env) *SystemdManager {
	return &SystemdManager{runner: runner, env: env}
}

func (s *SystemdManager) DaemonReload(ctx context.Context) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "daemon-reload")...)
}

func (s *SystemdManager) Enable(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "enable", "--now", service)...)
}

func (s *SystemdManager) Start(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "start", service)...)
}

func (s *SystemdManager) Stop(ctx context.Context, service string) error {
	return s.runner.Run(ctx, "systemctl", append(s.env.SystemctlArgs(), "stop", service)...)
}

func (s *SystemdManager) EnableLinger(ctx context.Context) error {
	if s.env.Mode == RootMode || s.env.Username == "" {
		return nil
	}
	return s.runner.Run(ctx, "loginctl", "enable-linger", s.env.Username)
}
