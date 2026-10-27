package cmd

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"

	"github.com/quay/quay/internal/installer"
)

func newInitCmd() *Command {
	return newInitCmdWithDeps(os.Stdin, runInitialize)
}

func newInitCmdWithDeps(stdin io.Reader, initialize func(context.Context, *installer.Config) int) *Command {
	fs := flag.NewFlagSet("init", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (optional, overrides flags)")
	dataDir := fs.String("data-dir", ".", "root directory for DB, storage, certs")
	hostname := fs.String("hostname", "localhost", "server hostname for generated configuration")
	initUser := fs.String("init-user", "admin", "admin username for initial setup")
	initPasswordStdin := fs.Bool("init-password-stdin", false, "read the initial admin password from stdin")

	// init runs inside the container image; end users provision through
	// install, so it is hidden from the top-level help listing.
	return &Command{
		Name:     "init",
		Synopsis: "Initialize the registry database and administrator",
		Flags:    fs,
		Hidden:   true,
		Run: func(ctx context.Context, _ *Command, _ []string) int {
			var password string
			if *initPasswordStdin {
				var err error
				password, err = readInitPassword(stdin)
				if err != nil {
					fmt.Fprintln(os.Stderr, "error: read initial password:", err)
					return 1
				}
			}
			return initialize(ctx, &installer.Config{
				ConfigPath:      *configPath,
				DataDir:         *dataDir,
				Hostname:        *hostname,
				InitUser:        *initUser,
				InitPassword:    password,
				InitPasswordSet: *initPasswordStdin,
			})
		},
	}
}

func runInitialize(ctx context.Context, cfg *installer.Config) int {
	if err := installer.Initialize(ctx, cfg); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		return 1
	}
	return 0
}
