// Package system provides OS-level abstractions for testability.
package system

import (
	"context"
	"io"
	"os/exec"
	"strings"
)

// CommandRunner abstracts external command execution.
type CommandRunner interface {
	Run(ctx context.Context, name string, args ...string) error
	Output(ctx context.Context, name string, args ...string) (string, error)
}

// ExecRunner implements CommandRunner using os/exec.
type ExecRunner struct {
	out io.Writer
}

func NewExecRunner(out io.Writer) *ExecRunner {
	return &ExecRunner{out: out}
}

func (r *ExecRunner) Run(ctx context.Context, name string, args ...string) error {
	cmd := exec.CommandContext(ctx, name, args...) //nolint:gosec // CLI tool, args from flags
	cmd.Stdout = r.out
	cmd.Stderr = r.out
	return cmd.Run()
}

func (r *ExecRunner) Output(ctx context.Context, name string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, name, args...) //nolint:gosec // CLI tool, args from flags
	cmd.Stderr = r.out
	out, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}
