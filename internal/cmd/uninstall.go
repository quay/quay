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
	dataDir := fs.String("data-dir", "/var/lib/quay", "directory for database, storage, and certs")
	autoApprove := fs.Bool("auto-approve", false, "skip confirmation prompt and remove data directory")

	return &Command{
		Name:     "uninstall",
		Synopsis: "Remove the registry service and optionally its data",
		Flags:    fs,
		Run: func(ctx context.Context, cmd *Command, _ []string) int {
			if !*autoApprove {
				if !confirmUninstall(stdin) {
					slog.Info("uninstall cancelled")
					return 0
				}
			}
			return uninstall(ctx, &uninstaller.Config{
				DataDir:     *dataDir,
				AutoApprove: *autoApprove,
			})
		},
	}
}

func confirmUninstall(r io.Reader) bool {
	fmt.Fprint(os.Stderr, "Are you sure you want to uninstall? [y/N]: ")
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
