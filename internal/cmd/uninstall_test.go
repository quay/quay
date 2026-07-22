package cmd

import (
	"bytes"
	"context"
	"strings"
	"testing"

	"github.com/quay/quay/internal/uninstaller"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUninstallCmdDefaultFlags(t *testing.T) {
	var captured *uninstaller.Config
	cmd := newUninstallCmdWithDeps(strings.NewReader(""), func(_ context.Context, cfg *uninstaller.Config) int {
		captured = cfg
		return 0
	})

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	require.Equal(t, 0, code)
	require.NotNil(t, captured)
	assert.Equal(t, "/var/lib/quay", captured.DataDir)
	assert.True(t, captured.AutoApprove)
}

func TestUninstallCmdCustomDataDir(t *testing.T) {
	var captured *uninstaller.Config
	cmd := newUninstallCmdWithDeps(strings.NewReader(""), func(_ context.Context, cfg *uninstaller.Config) int {
		captured = cfg
		return 0
	})

	code := cmd.Execute(t.Context(), []string{"-data-dir=/custom/path", "-auto-approve"})

	require.Equal(t, 0, code)
	require.NotNil(t, captured)
	assert.Equal(t, "/custom/path", captured.DataDir)
}

func TestUninstallCmdPromptsForConfirmation(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		wantCode int
		wantRun  bool
	}{
		{name: "y confirms", input: "y\n", wantCode: 0, wantRun: true},
		{name: "Y confirms", input: "Y\n", wantCode: 0, wantRun: true},
		{name: "yes confirms", input: "yes\n", wantCode: 0, wantRun: true},
		{name: "n cancels", input: "n\n", wantCode: 0, wantRun: false},
		{name: "empty cancels", input: "\n", wantCode: 0, wantRun: false},
		{name: "random cancels", input: "maybe\n", wantCode: 0, wantRun: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ran := false
			cmd := newUninstallCmdWithDeps(strings.NewReader(tt.input), func(_ context.Context, _ *uninstaller.Config) int {
				ran = true
				return 0
			})

			code := cmd.Execute(t.Context(), nil)

			assert.Equal(t, tt.wantCode, code)
			assert.Equal(t, tt.wantRun, ran)
		})
	}
}

func TestUninstallCmdAutoApproveSkipsPrompt(t *testing.T) {
	ran := false
	cmd := newUninstallCmdWithDeps(strings.NewReader(""), func(_ context.Context, _ *uninstaller.Config) int {
		ran = true
		return 0
	})

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	assert.Equal(t, 0, code)
	assert.True(t, ran)
}

func TestUninstallCmdReturnsRunExitCode(t *testing.T) {
	cmd := newUninstallCmdWithDeps(strings.NewReader(""), func(_ context.Context, _ *uninstaller.Config) int {
		return 1
	})

	code := cmd.Execute(t.Context(), []string{"-auto-approve"})

	assert.Equal(t, 1, code)
}

func TestUninstallCmdHelp(t *testing.T) {
	cmd := newUninstallCmdWithDeps(strings.NewReader(""), func(_ context.Context, _ *uninstaller.Config) int {
		return 0
	})

	var buf bytes.Buffer
	cmd.Usage(&buf)

	assert.Contains(t, buf.String(), "uninstall")
	assert.Contains(t, buf.String(), "-data-dir")
	assert.Contains(t, buf.String(), "-auto-approve")
}
