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
	Runner CommandRunner
	Env    *Env
}

func (s *SystemdManager) DaemonReload(ctx context.Context) error {
	return s.Runner.Run(ctx, "systemctl", append(s.Env.SystemctlArgs(), "daemon-reload")...)
}

func (s *SystemdManager) Enable(ctx context.Context, service string) error {
	return s.Runner.Run(ctx, "systemctl", append(s.Env.SystemctlArgs(), "enable", "--now", service)...)
}

func (s *SystemdManager) Start(ctx context.Context, service string) error {
	return s.Runner.Run(ctx, "systemctl", append(s.Env.SystemctlArgs(), "start", service)...)
}

func (s *SystemdManager) Stop(ctx context.Context, service string) error {
	return s.Runner.Run(ctx, "systemctl", append(s.Env.SystemctlArgs(), "stop", service)...)
}

func (s *SystemdManager) EnableLinger(ctx context.Context) error {
	if s.Env.Mode == RootMode || s.Env.Username == "" {
		return nil
	}
	return s.Runner.Run(ctx, "loginctl", "enable-linger", s.Env.Username)
}
