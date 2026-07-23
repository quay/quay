package system

import (
	"context"
	"errors"
	"os/exec"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// exitError returns a real *exec.ExitError with the given exit code by running
// a shell process that exits with that code.
func exitError(t *testing.T, code int) *exec.ExitError {
	t.Helper()
	cmd := exec.Command("sh", "-c", "exit "+string(rune('0'+code)))
	err := cmd.Run()
	require.Error(t, err)
	var exitErr *exec.ExitError
	require.True(t, errors.As(err, &exitErr))
	return exitErr
}

type recordingRunner struct {
	calls []string
	err   error
}

func (r *recordingRunner) Run(_ context.Context, name string, args ...string) error {
	call := name
	for _, a := range args {
		call += " " + a
	}
	r.calls = append(r.calls, call)
	return r.err
}

func (r *recordingRunner) Output(_ context.Context, name string, args ...string) (string, error) {
	return "", r.err
}

var _ CommandRunner = (*recordingRunner)(nil)

func TestStopWrapsExitCode5AsErrUnitNotFound(t *testing.T) {
	runner := &recordingRunner{err: exitError(t, 5)}
	mgr := NewSystemdManager(runner, &Env{Mode: UserMode, HomeDir: t.TempDir()})

	err := mgr.Stop(t.Context(), "quay")

	require.Error(t, err)
	assert.True(t, errors.Is(err, ErrUnitNotFound))
	assert.Contains(t, runner.calls[0], "stop")
}

func TestStopPreservesNonExitCode5Errors(t *testing.T) {
	runner := &recordingRunner{err: exitError(t, 1)}
	mgr := NewSystemdManager(runner, &Env{Mode: UserMode, HomeDir: t.TempDir()})

	err := mgr.Stop(t.Context(), "quay")

	require.Error(t, err)
	assert.False(t, errors.Is(err, ErrUnitNotFound))
	var exitErr *exec.ExitError
	assert.True(t, errors.As(err, &exitErr))
}

func TestStopReturnsNilOnSuccess(t *testing.T) {
	runner := &recordingRunner{}
	mgr := NewSystemdManager(runner, &Env{Mode: UserMode, HomeDir: t.TempDir()})

	err := mgr.Stop(t.Context(), "quay")

	require.NoError(t, err)
	assert.Contains(t, runner.calls[0], "stop quay")
}

func TestDisableLingerCallsLoginctlInUserMode(t *testing.T) {
	runner := &recordingRunner{}
	mgr := NewSystemdManager(runner, &Env{Mode: UserMode, HomeDir: t.TempDir(), Username: "testuser"})

	err := mgr.DisableLinger(t.Context())

	require.NoError(t, err)
	require.Len(t, runner.calls, 1)
	assert.Equal(t, "loginctl disable-linger testuser", runner.calls[0])
}

func TestDisableLingerSkipsInRootMode(t *testing.T) {
	runner := &recordingRunner{}
	mgr := NewSystemdManager(runner, &Env{Mode: RootMode})

	err := mgr.DisableLinger(t.Context())

	require.NoError(t, err)
	assert.Empty(t, runner.calls)
}

func TestDisableLingerSkipsWhenUsernameEmpty(t *testing.T) {
	runner := &recordingRunner{}
	mgr := NewSystemdManager(runner, &Env{Mode: UserMode, HomeDir: t.TempDir(), Username: ""})

	err := mgr.DisableLinger(t.Context())

	require.NoError(t, err)
	assert.Empty(t, runner.calls)
}
