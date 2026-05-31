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

// Run is the CLI entry point. It constructs the command tree and returns
// the process exit code.
func Run(args []string) int {
	fs := flag.NewFlagSet("quay", flag.ContinueOnError)
	logLevel := fs.String("log-level", "", "log level: debug, info, warn, error (default: info)")
	logFormat := fs.String("log-format", "", "log format: json, text (default: json)")

	root := &Command{
		Name:     "quay",
		Synopsis: "OCI container registry",
		Flags:    fs,
		Subcommands: []*Command{
			newInstallCmd(),
			newConfigCmd(),
			newServeCmd(),
			newVersionCmd(),
		},
		AfterParse: func() error {
			level, format := logging.ResolveConfig(*logLevel, *logFormat, "", "")
			return logging.Setup(level, format, os.Stderr)
		},
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	return root.Execute(ctx, args[1:])
}
