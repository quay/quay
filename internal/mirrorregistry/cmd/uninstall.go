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

func newUninstallCmd() *Command {
	return newUninstallCmdWithDeps(os.Stdin, runUninstall)
}

func newUninstallCmdWithDeps(stdin io.Reader, uninstall func(context.Context, *uninstaller.Config) int) *Command {
	fs := flag.NewFlagSet("uninstall", flag.ContinueOnError)
	dataDir := fs.String("data-dir", "", "directory for database, storage, and certs (auto-detected from installation)")
	autoApprove := fs.Bool("auto-approve", false, "skip confirmation prompt")
	purge := fs.Bool("purge", false, "remove the data directory (database, storage, and certs)")

	return &Command{
		Name:     "uninstall",
		Synopsis: "Remove the registry service and optionally its data",
		Flags:    fs,
		Run: func(ctx context.Context, cmd *Command, _ []string) int {
			if !*autoApprove {
				if !confirmUninstall(stdin, *purge, *dataDir) {
					slog.Info("uninstall canceled")
					return 0
				}
			}
			return uninstall(ctx, &uninstaller.Config{
				DataDir:     *dataDir,
				AutoApprove: *autoApprove,
				Purge:       *purge,
			})
		},
	}
}

func confirmUninstall(r io.Reader, purge bool, dataDir string) bool {
	if purge {
		fmt.Fprintf(os.Stderr, "Are you sure you want to uninstall and delete all data at %s? [y/N]: ", dataDir)
	} else {
		fmt.Fprint(os.Stderr, "Are you sure you want to uninstall? Data will be preserved. [y/N]: ")
	}
	scanner := bufio.NewScanner(r)
	if !scanner.Scan() {
		return false
	}
	answer := strings.TrimSpace(scanner.Text())
	return strings.EqualFold(answer, "y") || strings.EqualFold(answer, "yes")
}

func runUninstall(ctx context.Context, cfg *uninstaller.Config) int {
	u, err := uninstaller.New(os.Stderr)
	if err != nil {
		slog.Error("uninstaller setup failed", "err", err)
		return 1
	}

	if err := u.Run(ctx, cfg); err != nil {
		slog.Error("uninstall failed", "err", err)
		return 1
	}

	return 0
}
