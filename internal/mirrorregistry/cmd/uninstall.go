package cmd

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/quay/quay/internal/uninstaller"
)

// uninstallRunner is the subset of *uninstaller.Uninstaller the command
// needs: resolving the data directory up front so the confirmation prompt
// can show the real deletion target, then performing the uninstall.
type uninstallRunner interface {
	ResolveDataDir(*uninstaller.Config) error
	Run(context.Context, *uninstaller.Config) error
}

func newUninstallCmd() *Command {
	return newUninstallCmdWithDeps(os.Stdin, os.Stderr, func() (uninstallRunner, error) {
		return uninstaller.New(os.Stderr)
	})
}

func newUninstallCmdWithDeps(stdin io.Reader, stderr io.Writer, newRunner func() (uninstallRunner, error)) *Command {
	fs := flag.NewFlagSet("uninstall", flag.ContinueOnError)
	dataDir := fs.String("data-dir", "", "directory for database, storage, and certs (auto-detected from installation)")
	autoApprove := fs.Bool("auto-approve", false, "skip confirmation prompt")
	purge := fs.Bool("purge", false, "remove the data directory (database, storage, and certs)")

	return &Command{
		Name:     "uninstall",
		Synopsis: "Remove the registry service and optionally its data",
		Flags:    fs,
		Run: func(ctx context.Context, _ *Command, _ []string) int {
			runner, err := newRunner()
			if err != nil {
				slog.Error("uninstaller setup failed", "err", err)
				return 1
			}
			cfg := &uninstaller.Config{DataDir: *dataDir, Purge: *purge}
			if err := runner.ResolveDataDir(cfg); err != nil {
				slog.Error("uninstall failed", "err", err)
				return 1
			}
			if !*autoApprove && !confirmUninstall(stdin, stderr, cfg) {
				slog.Info("uninstall canceled")
				return 0
			}
			if err := runner.Run(ctx, cfg); err != nil {
				slog.Error("uninstall failed", "err", err)
				return 1
			}
			return 0
		},
	}
}

func confirmUninstall(r io.Reader, w io.Writer, cfg *uninstaller.Config) bool {
	switch {
	case cfg.Purge:
		fmt.Fprintf(w, "Are you sure you want to uninstall and delete all data at %s? [y/N]: ", cfg.DataDir)
	case cfg.DataDir != "":
		fmt.Fprintf(w, "Are you sure you want to uninstall? Data at %s will be preserved. [y/N]: ", cfg.DataDir)
	default:
		fmt.Fprint(w, "Are you sure you want to uninstall? [y/N]: ")
	}
	scanner := bufio.NewScanner(r)
	if !scanner.Scan() {
		return false
	}
	answer := strings.TrimSpace(scanner.Text())
	return strings.EqualFold(answer, "y") || strings.EqualFold(answer, "yes")
}
