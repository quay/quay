package migrate

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

func TestCleanup_RemovesUnitFiles(t *testing.T) {
	dir := t.TempDir()
	unitPath := filepath.Join(dir, "quay-app.service")
	os.WriteFile(unitPath, []byte("[Unit]\nDescription=test"), 0o644)

	m := &Migrator{
		Out: &bytes.Buffer{},
		Source: OMRSource{
			UnitFiles:    []string{unitPath},
			SystemdScope: "user",
		},
	}

	if err := m.removeUnitFiles(); err != nil {
		t.Fatalf("removeUnitFiles: %v", err)
	}

	if _, err := os.Stat(unitPath); !os.IsNotExist(err) {
		t.Error("unit file should have been removed")
	}
}

func TestCleanup_SkipsWhenNoUnits(t *testing.T) {
	m := &Migrator{
		Out:    &bytes.Buffer{},
		Source: OMRSource{},
	}

	if err := m.removeUnitFiles(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// exitError mimics exec.ExitError's exit code.
type exitError int

func (e exitError) Error() string { return fmt.Sprintf("exit status %d", int(e)) }
func (e exitError) ExitCode() int { return int(e) }

// cleanupRunner fails the exact calls listed in errs.
type cleanupRunner struct {
	calls []string
	errs  map[string]error
}

func (r *cleanupRunner) Run(_ context.Context, name string, args ...string) error {
	call := name + " " + strings.Join(args, " ")
	r.calls = append(r.calls, call)
	return r.errs[call]
}

func (*cleanupRunner) Output(context.Context, string, ...string) (string, error) {
	return "", nil
}

func cleanupMigrator(t *testing.T, scope string, runner *cleanupRunner) *Migrator {
	t.Helper()
	dir := t.TempDir()
	var units []string
	for _, svc := range omrServiceNames {
		path := filepath.Join(dir, svc+".service")
		if err := os.WriteFile(path, []byte("[Unit]\n"), 0o600); err != nil {
			t.Fatal(err)
		}
		units = append(units, path)
	}
	return &Migrator{
		Out:    &bytes.Buffer{},
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scope,
			UnitFiles:    units,
			VolumeNames:  []string{"sqlite-storage", "quay-storage"},
		},
	}
}

func TestCleanup_StopsServicesAndRemovesContainersBeforeVolumes(t *testing.T) {
	for _, tc := range []struct {
		scope     string
		systemctl string
	}{
		{scope: scopeSystem, systemctl: "systemctl "},
		{scope: scopeUser, systemctl: "systemctl --user "},
	} {
		t.Run(tc.scope, func(t *testing.T) {
			runner := &cleanupRunner{}
			m := cleanupMigrator(t, tc.scope, runner)

			if err := m.cleanup(t.Context()); err != nil {
				t.Fatalf("cleanup: %v", err)
			}
			want := []string{
				tc.systemctl + "stop quay-app.service",
				tc.systemctl + "stop quay-redis.service",
				tc.systemctl + "stop quay-pod.service",
				tc.systemctl + "disable quay-app.service",
				tc.systemctl + "disable quay-redis.service",
				tc.systemctl + "disable quay-pod.service",
				"podman container exists quay-app",
				"podman container stop quay-app",
				"podman container rm quay-app",
				"podman pod exists quay-pod",
				"podman pod stop quay-pod",
				"podman pod rm quay-pod",
				"podman volume exists sqlite-storage",
				"podman volume rm sqlite-storage",
				"podman volume exists quay-storage",
				"podman volume rm quay-storage",
				"podman secret rm redis_pass",
				tc.systemctl + "daemon-reload",
			}
			if strings.Join(runner.calls, "\n") != strings.Join(want, "\n") {
				t.Fatalf("calls =\n%s\nwant\n%s", strings.Join(runner.calls, "\n"), strings.Join(want, "\n"))
			}
			for _, path := range m.Source.UnitFiles {
				if _, err := os.Stat(path); !os.IsNotExist(err) {
					t.Errorf("unit file %s not removed: %v", path, err)
				}
			}
		})
	}
}

func TestCleanup_AcceptsAlreadyRemovedObjects(t *testing.T) {
	runner := &cleanupRunner{errs: map[string]error{
		"podman container exists quay-app":    exitError(1),
		"podman pod exists quay-pod":          exitError(1),
		"podman volume exists sqlite-storage": exitError(1),
		"podman volume exists quay-storage":   exitError(1),
		"podman secret rm redis_pass":         exitError(1),
	}}
	m := cleanupMigrator(t, scopeSystem, runner)
	// A rerun after a cleanup that removed the unit files finds none.
	m.Source.UnitFiles = nil

	if err := m.cleanup(t.Context()); err != nil {
		t.Fatalf("cleanup: %v", err)
	}
	for _, call := range runner.calls {
		if strings.Contains(call, " stop ") || strings.Contains(call, " rm quay-") || strings.Contains(call, "volume rm") || strings.Contains(call, " disable ") {
			t.Errorf("cleanup acted on an absent object: %q", call)
		}
	}
}

func TestCleanup_ReportsPodmanFailures(t *testing.T) {
	for _, tc := range []struct {
		name    string
		failing string
		want    string
	}{
		{name: "volume in use", failing: "podman volume rm sqlite-storage", want: "podman volume rm sqlite-storage: exit status 2"},
		{name: "exists check fails", failing: "podman pod exists quay-pod", want: "check podman pod quay-pod: exit status 125"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			code := exitError(2)
			if strings.Contains(tc.failing, "exists") {
				code = exitError(125)
			}
			runner := &cleanupRunner{errs: map[string]error{tc.failing: code}}
			m := cleanupMigrator(t, scopeSystem, runner)

			err := m.cleanup(t.Context())
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("cleanup error = %v, want %q", err, tc.want)
			}
			// Unit files stay, so a rerun still detects the old OMR.
			for _, path := range m.Source.UnitFiles {
				if _, err := os.Stat(path); err != nil {
					t.Errorf("unit file %s removed after a failed cleanup: %v", path, err)
				}
			}
		})
	}
}

func TestCleanup_DisableFailureNamesUnit(t *testing.T) {
	runner := &cleanupRunner{errs: map[string]error{"systemctl --user disable quay-redis.service": exitError(1)}}
	m := cleanupMigrator(t, scopeUser, runner)

	err := m.cleanup(t.Context())
	if err == nil || !strings.Contains(err.Error(), "disable quay-redis.service") {
		t.Fatalf("cleanup error = %v, want the failed unit named", err)
	}
	for _, call := range runner.calls {
		if strings.HasPrefix(call, "podman ") {
			t.Fatalf("cleanup removed podman objects after a failed disable: %v", runner.calls)
		}
	}
}

func TestCleanup_StopFailureStillDisablesUnits(t *testing.T) {
	runner := &cleanupRunner{errs: map[string]error{"systemctl --user stop quay-app.service": exitError(5)}}
	m := cleanupMigrator(t, scopeUser, runner)

	if err := m.cleanup(t.Context()); err != nil {
		t.Fatalf("cleanup: %v", err)
	}
	if !slices.Contains(runner.calls, "systemctl --user disable quay-app.service") {
		t.Fatalf("cleanup did not disable quay-app.service after a failed stop: %v", runner.calls)
	}
}
