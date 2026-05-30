// Package cmd implements the quay CLI subcommand dispatch.
package cmd

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
)

const (
	helpFlag       = "--help"
	helpLiteral    = "help"
	versionLiteral = "version"
)

// Run is the CLI entry point. It dispatches to subcommands based on os.Args
// and returns the process exit code.
func Run(args []string) int {
	if len(args) < 2 {
		usage()
		return 1
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	switch args[1] {
	case "config":
		return runConfig(ctx, args[2:])
	case "install":
		return runInstall(ctx, args[2:])
	case "serve":
		return runServe(ctx, args[2:])
	case versionLiteral:
		return runVersion()
	case helpLiteral, "-h", helpFlag:
		usage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", args[1])
		usage()
		return 1
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, `usage: quay <command> [flags]

commands:
  install           Set up or upgrade registry (Quadlet service)
  config            Configuration tools (validate)
  serve             Start the OCI container registry
  version           Print version information`)
}
