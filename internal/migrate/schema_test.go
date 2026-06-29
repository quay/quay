package migrate

import (
	"bytes"
	"context"
	"errors"
	"path/filepath"
	"strings"
	"testing"

	"github.com/quay/quay/internal/dal/dbcore"
)

func TestUpgradeSchema_AlreadyCurrent(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay.db")

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatalf("OpenSQLite: %v", err)
	}
	if err := dbcore.InitDatabase(t.Context(), db, &bytes.Buffer{}); err != nil {
		t.Fatalf("InitDatabase: %v", err)
	}
	db.Close()

	m := &Migrator{
		DataDir: dir,
		Out:     &bytes.Buffer{},
	}

	if err := m.upgradeSchema(t.Context()); err != nil {
		t.Fatalf("upgradeSchema: %v", err)
	}
}

func TestStopOldOMR_ReturnsErrorWhenQuayAppStopFails(t *testing.T) {
	runner := &recordingRunner{
		runErrs: map[string]error{
			"quay-app.service": errors.New("permission denied"),
		},
	}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
			UnitFiles:    []string{"/etc/systemd/system/quay-app.service"},
		},
	}

	err := m.stopOldOMR(t.Context())
	if err == nil {
		t.Fatal("expected stopOldOMR to fail when quay-app cannot stop")
	}
	if !strings.Contains(err.Error(), "quay-app") {
		t.Fatalf("expected error to mention quay-app, got %v", err)
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("expected stopOldOMR to attempt all services, got %d calls", len(runner.runCalls))
	}
}

func TestStopOldOMR_ReturnsErrorWhenRedisOrPodStopFails(t *testing.T) {
	runner := &recordingRunner{
		runErrs: map[string]error{
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

	err := m.stopOldOMR(t.Context())
	if err == nil {
		t.Fatal("expected stopOldOMR to fail when any service cannot stop")
	}
	for _, svc := range []string{"quay-redis", "quay-pod"} {
		if !strings.Contains(err.Error(), svc) {
			t.Fatalf("expected error to mention %s, got %v", svc, err)
		}
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("expected stopOldOMR to attempt all services, got %d calls", len(runner.runCalls))
	}
}

func TestStopOldOMR_SkipsWhenNoUnitFilesDetected(t *testing.T) {
	runner := &recordingRunner{}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
		},
	}

	if err := m.stopOldOMR(t.Context()); err != nil {
		t.Fatalf("stopOldOMR should skip when no unit files were detected: %v", err)
	}
	if len(runner.runCalls) != 0 {
		t.Fatalf("expected no stop calls when no unit files were detected, got %d", len(runner.runCalls))
	}
}

func TestStopOldOMR_SucceedsWhenAllStopsSucceed(t *testing.T) {
	runner := &recordingRunner{}
	m := &Migrator{
		Runner: runner,
		Source: OMRSource{
			SystemdScope: scopeSystem,
			UnitFiles:    []string{"/etc/systemd/system/quay-app.service"},
		},
	}

	if err := m.stopOldOMR(t.Context()); err != nil {
		t.Fatalf("stopOldOMR should succeed when all stop commands succeed: %v", err)
	}
	if len(runner.runCalls) != len(omrServiceNames) {
		t.Fatalf("expected stopOldOMR to attempt all services, got %d calls", len(runner.runCalls))
	}
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
