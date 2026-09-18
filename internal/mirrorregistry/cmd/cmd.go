// Package cmd implements the quay CLI subcommand dispatch.
package cmd

import (
	"context"
	"flag"
	"os"
	"os/signal"
	"syscall"

	"github.com/quay/quay/internal/logging"
)

// BinaryName is the name of the shipped CLI binary. It is printed in usage
// output and must match GO_BINARY_NAME in the Makefile and the container
// image entrypoint in Dockerfile.mirror.
const BinaryName = "mirror-registry"

// Run is the CLI entry point. It constructs the command tree and returns
// the process exit code.
func Run(args []string) int {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	return newRootCmd().Execute(ctx, args[1:])
}

func newRootCmd() *Command {
	fs := flag.NewFlagSet(BinaryName, flag.ContinueOnError)
	logLevel := fs.String("log-level", "", "log level: debug, info, warn, error (default: info)")
	logFormat := fs.String("log-format", "", "log format: json, text (default: json)")

	return &Command{
		Name:     BinaryName,
		Synopsis: "OCI container registry",
		Flags:    fs,
		Subcommands: []*Command{
			newInstallCmd(),
			newUninstallCmd(),
			newInitCmd(),
			newConfigCmd(),
			newServeCmd(),
			newMigrateCmd(),
			newVersionCmd(),
		},
		AfterParse: func() error {
			level, format := logging.ResolveConfig(*logLevel, *logFormat, "", "")
			return logging.Setup(level, format, os.Stderr)
		},
	}
}
