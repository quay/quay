package migrate

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRuntimeConfigPort(t *testing.T) {
	tests := []struct {
		name     string
		hostname string
		want     string
	}{
		{name: "custom port", hostname: "registry.example.com:9443", want: "9443"},
		{name: "default port", hostname: "registry.example.com", want: "8443"},
		{name: "IPv6", hostname: "[2001:db8::1]:10443", want: "10443"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), runtimeConfigFile)
			require.NoError(t, os.WriteFile(path, []byte("SERVER_HOSTNAME: \""+tt.hostname+"\"\n"), 0o600))

			port, err := runtimeConfigPort(path)

			require.NoError(t, err)
			assert.Equal(t, tt.want, port)
		})
	}
}

func TestStopSourceServices_SucceedsWhenQuayAppAlreadyStopped(t *testing.T) {
	runner := &recordingRunner{
		runErrs: map[string]error{
			"quay-app.service": errors.New("Unit quay-app.service not loaded"),
		},
	}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
			UnitFiles:    []string{"/etc/systemd/system/quay-app.service"},
		},
	}

	if err := m.stopSourceServices(t.Context()); err != nil {
		t.Fatalf("stopSourceServices should succeed when services are already stopped: %v", err)
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("expected stopSourceServices to attempt all services, got %d calls", len(runner.runCalls))
	}
}

func TestStopSourceServices_SucceedsWhenAllServicesAlreadyStopped(t *testing.T) {
	runner := &recordingRunner{
		runErrs: map[string]error{
			"quay-app.service":   errors.New("already stopped"),
			"quay-redis.service": errors.New("already stopped"),
			"quay-pod.service":   errors.New("already stopped"),
		},
	}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
			UnitFiles:    []string{"/etc/systemd/system/quay-app.service"},
		},
	}

	if err := m.stopSourceServices(t.Context()); err != nil {
		t.Fatalf("stopSourceServices should succeed even when all services are already stopped: %v", err)
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("expected stopSourceServices to attempt all services, got %d calls", len(runner.runCalls))
	}
}

func TestStopSourceServices_SkipsWhenNoUnitFilesDetected(t *testing.T) {
	runner := &recordingRunner{
		runErrs: map[string]error{
			"quay-app.service": errors.New("inactive"),
		},
	}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
		},
	}

	if err := m.stopSourceServices(t.Context()); err != nil {
		t.Fatalf("stopSourceServices should skip when no unit files were detected: %v", err)
	}
	for _, call := range runner.runCalls {
		if strings.Contains(call, "stop") {
			t.Fatalf("expected no stop calls when no services are active, got: %s", call)
		}
	}
}

func TestStopSourceServices_SucceedsWhenAllStopsSucceed(t *testing.T) {
	runner := &recordingRunner{}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
			UnitFiles:    []string{"/etc/systemd/system/quay-app.service"},
		},
	}

	if err := m.stopSourceServices(t.Context()); err != nil {
		t.Fatalf("stopSourceServices should succeed when all stop commands succeed: %v", err)
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("expected stopSourceServices to attempt all services, got %d calls", len(runner.runCalls))
	}
}

func TestStopSourceServices_DiscoversActiveServicesWhenUnitFilesEmpty(t *testing.T) {
	runner := &recordingRunner{}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{},
	}

	if err := m.stopSourceServices(t.Context()); err != nil {
		t.Fatalf("stopSourceServices should succeed: %v", err)
	}

	var probes, stops int
	for _, call := range runner.runCalls {
		if strings.Contains(call, "is-active") {
			probes++
		}
		if strings.Contains(call, "stop") {
			stops++
		}
	}
	if probes == 0 {
		t.Fatal("expected discovery probes when UnitFiles is empty")
	}
	if stops != len(omrServiceNames) {
		t.Fatalf("expected %d stop calls after discovery, got %d", len(omrServiceNames), stops)
	}
	if m.Source.SystemdScope == "" {
		t.Fatal("expected discovered scope to be persisted to Source.SystemdScope")
	}
}

func TestStopSourceServices_DiscoveryProbesSystemFirst(t *testing.T) {
	runner := &recordingRunner{}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{},
	}

	_ = m.stopSourceServices(t.Context())

	var stops int
	for _, call := range runner.runCalls {
		if strings.Contains(call, "stop") {
			stops++
			if strings.Contains(call, "--user") {
				t.Fatalf("expected system scope (probed first), got user scope: %s", call)
			}
		}
	}
	if stops != len(omrServiceNames) {
		t.Fatalf("expected %d system-scope stop calls, got %d", len(omrServiceNames), stops)
	}
}

func TestStopSourceServices_DiscoveryFallsToUserScope(t *testing.T) {
	runner := &scopeAwareRunner{
		userActive:   true,
		systemActive: false,
	}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{},
	}

	if err := m.stopSourceServices(t.Context()); err != nil {
		t.Fatalf("stopSourceServices should succeed: %v", err)
	}

	var stops int
	for _, call := range runner.calls {
		if strings.Contains(call, "stop") {
			stops++
			if !strings.Contains(call, "--user") {
				t.Fatalf("expected user scope stop calls, got system scope: %s", call)
			}
		}
	}
	if stops != len(omrServiceNames) {
		t.Fatalf("expected %d user-scope stop calls, got %d", len(omrServiceNames), stops)
	}
}

func TestStopSourceServices_NoOpWhenNeitherScopeHasActiveServices(t *testing.T) {
	runner := &scopeAwareRunner{
		userActive:   false,
		systemActive: false,
	}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{},
	}

	err := m.stopSourceServices(t.Context())

	require.NoError(t, err)
	var probes int
	for _, call := range runner.calls {
		if strings.Contains(call, "is-active") {
			probes++
		}
		if strings.Contains(call, "stop") {
			t.Fatalf("expected zero stop calls when no services are active, got: %s", call)
		}
	}
	if probes < 2 {
		t.Fatalf("expected probes in both scopes, got %d", probes)
	}
}

func TestStopSourceServices_SkipsWhenRunnerIsNil(t *testing.T) {
	m := &Migrator{
		Runner: nil,
		Source: OMRSource{},
	}

	err := m.stopSourceServices(t.Context())

	require.NoError(t, err)
}

type recordingRunner struct {
	runCalls []string
	runErrs  map[string]error
}

func (r *recordingRunner) Run(_ context.Context, name string, args ...string) error {
	r.runCalls = append(r.runCalls, name+" "+strings.Join(args, " "))
	if len(args) == 0 {
		return nil
	}
	return r.runErrs[args[len(args)-1]]
}

func (r *recordingRunner) Output(_ context.Context, _ string, _ ...string) (string, error) {
	return "", nil
}

type scopeAwareRunner struct {
	userActive   bool
	systemActive bool
	calls        []string
}

func (r *scopeAwareRunner) Run(_ context.Context, name string, args ...string) error {
	call := name + " " + strings.Join(args, " ")
	r.calls = append(r.calls, call)
	if strings.Contains(call, "is-active") {
		if strings.Contains(call, "--user") && !r.userActive {
			return errors.New("inactive")
		}
		if !strings.Contains(call, "--user") && !r.systemActive {
			return errors.New("inactive")
		}
	}
	return nil
}

func (r *scopeAwareRunner) Output(_ context.Context, _ string, _ ...string) (string, error) {
	return "", nil
}
