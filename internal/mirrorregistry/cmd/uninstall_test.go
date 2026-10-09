package cmd

import (
	"bytes"
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/quay/quay/internal/uninstaller"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// fakeUninstallRunner records the order of calls and lets tests control
// what ResolveDataDir fills in and whether Run fails.
type fakeUninstallRunner struct {
	calls       []string
	resolvedDir string
	resolveErr  error
	runErr      error
	captured    *uninstaller.Config
}

func (f *fakeUninstallRunner) ResolveDataDir(cfg *uninstaller.Config) error {
	f.calls = append(f.calls, "resolve")
	if f.resolveErr != nil {
		return f.resolveErr
	}
	if cfg.DataDir == "" {
		cfg.DataDir = f.resolvedDir
	}
	return nil
}

func (f *fakeUninstallRunner) Run(_ context.Context, cfg *uninstaller.Config) error {
	f.calls = append(f.calls, "run")
	f.captured = cfg
	return f.runErr
}

func newTestUninstallCmd(stdin string, runner *fakeUninstallRunner) (*Command, *bytes.Buffer) {
	var stderr bytes.Buffer
	cmd := newUninstallCmdWithDeps(strings.NewReader(stdin), &stderr, func() (uninstallRunner, error) {
		return runner, nil
	})
	return cmd, &stderr
}

func TestUninstallCmdDefaultFlags(t *testing.T) {
	runner := &fakeUninstallRunner{}
	cmd, _ := newTestUninstallCmd("", runner)

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	require.Equal(t, 0, code)
	require.NotNil(t, runner.captured)
	assert.Equal(t, "", runner.captured.DataDir, "data-dir should default to empty for auto-detection")
	assert.False(t, runner.captured.Purge)
}

func TestUninstallCmdCustomDataDir(t *testing.T) {
	runner := &fakeUninstallRunner{resolvedDir: "/from/quadlet"}
	cmd, _ := newTestUninstallCmd("", runner)

	code := cmd.Execute(t.Context(), []string{"-data-dir=/custom/path", "-auto-approve"})

	require.Equal(t, 0, code)
	require.NotNil(t, runner.captured)
	assert.Equal(t, "/custom/path", runner.captured.DataDir, "explicit -data-dir must win over auto-detection")
}

func TestUninstallCmdPromptsForConfirmation(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		wantRun bool
	}{
		{name: "y confirms", input: "y\n", wantRun: true},
		{name: "Y confirms", input: "Y\n", wantRun: true},
		{name: "yes confirms", input: "yes\n", wantRun: true},
		{name: "n cancels", input: "n\n", wantRun: false},
		{name: "empty cancels", input: "\n", wantRun: false},
		{name: "random cancels", input: "maybe\n", wantRun: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			runner := &fakeUninstallRunner{}
			cmd, _ := newTestUninstallCmd(tt.input, runner)

			code := cmd.Execute(t.Context(), nil)

			assert.Equal(t, 0, code)
			assert.Equal(t, tt.wantRun, runner.captured != nil)
		})
	}
}

func TestUninstallCmdAutoApproveSkipsPrompt(t *testing.T) {
	runner := &fakeUninstallRunner{}
	cmd, stderr := newTestUninstallCmd("", runner)

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	assert.Equal(t, 0, code)
	assert.NotNil(t, runner.captured)
	assert.NotContains(t, stderr.String(), "Are you sure")
}

func TestUninstallCmdPurgeFlag(t *testing.T) {
	runner := &fakeUninstallRunner{}
	cmd, _ := newTestUninstallCmd("", runner)

	code := cmd.Execute(t.Context(), []string{"-auto-approve", "-purge"})

	require.Equal(t, 0, code)
	require.NotNil(t, runner.captured)
	assert.True(t, runner.captured.Purge)
}

func TestUninstallCmdAutoApproveDoesNotSetPurge(t *testing.T) {
	runner := &fakeUninstallRunner{}
	cmd, _ := newTestUninstallCmd("", runner)

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	require.Equal(t, 0, code)
	require.NotNil(t, runner.captured)
	assert.False(t, runner.captured.Purge, "auto-approve alone should not set purge")
}

func TestUninstallCmdResolvesDataDirBeforePurgePrompt(t *testing.T) {
	runner := &fakeUninstallRunner{resolvedDir: "/srv/quay-data"}
	cmd, stderr := newTestUninstallCmd("n\n", runner)

	code := cmd.Execute(t.Context(), []string{"-purge"})

	assert.Equal(t, 0, code)
	assert.Equal(t, []string{"resolve"}, runner.calls, "must resolve before prompting and not run after cancel")
	assert.Contains(t, stderr.String(), "delete all data at /srv/quay-data",
		"prompt must show the resolved deletion target")
}

func TestUninstallCmdPreservePromptShowsResolvedDataDir(t *testing.T) {
	runner := &fakeUninstallRunner{resolvedDir: "/srv/quay-data"}
	cmd, stderr := newTestUninstallCmd("y\n", runner)

	code := cmd.Execute(t.Context(), nil)

	assert.Equal(t, 0, code)
	assert.Equal(t, []string{"resolve", "run"}, runner.calls)
	assert.Contains(t, stderr.String(), "Data at /srv/quay-data will be preserved")
}

func TestUninstallCmdFailsWhenPurgeTargetCannotBeResolved(t *testing.T) {
	runner := &fakeUninstallRunner{resolveErr: errors.New("no Volume= directive")}
	cmd, stderr := newTestUninstallCmd("y\n", runner)

	code := cmd.Execute(t.Context(), []string{"-purge"})

	assert.Equal(t, 1, code)
	assert.Equal(t, []string{"resolve"}, runner.calls, "must not prompt or run when resolution fails")
	assert.NotContains(t, stderr.String(), "Are you sure")
}

func TestUninstallCmdReturnsRunExitCode(t *testing.T) {
	runner := &fakeUninstallRunner{runErr: errors.New("boom")}
	cmd, _ := newTestUninstallCmd("", runner)

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	assert.Equal(t, 1, code)
}

func TestUninstallCmdReturnsSetupError(t *testing.T) {
	cmd := newUninstallCmdWithDeps(strings.NewReader(""), &bytes.Buffer{}, func() (uninstallRunner, error) {
		return nil, errors.New("detect environment")
	})

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	assert.Equal(t, 1, code)
}

func TestUninstallCmdHelp(t *testing.T) {
	cmd, _ := newTestUninstallCmd("", &fakeUninstallRunner{})

	var buf bytes.Buffer
	cmd.Usage(&buf)

	assert.Contains(t, buf.String(), "uninstall")
	assert.Contains(t, buf.String(), "-data-dir")
	assert.Contains(t, buf.String(), "-auto-approve")
	assert.Contains(t, buf.String(), "-purge")
}
