// Package cmd implements the quay CLI subcommand dispatch.
package cmd

import (
	"fmt"
	"os"
)

// Run is the CLI entry point. It dispatches to subcommands based on os.Args
// and returns the process exit code.
func Run(args []string) int {
	if len(args) < 2 {
		usage()
		return 1
	}

	switch args[1] {
	case "config":
		return runConfig(args[2:])
	case "db":
		return runDB(args[2:])
	case "serve":
		return runServe(args[2:])
	case "version":
		return runVersion()
	case "help", "-h", "--help":
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
  config            Configuration tools (validate)
  db                Database lifecycle (init, version, upgrade)
  serve             Start a minimal OCI container registry
  version           Print version information`)
}
