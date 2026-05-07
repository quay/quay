// Package cmd implements the quay CLI subcommand dispatch.
package cmd

import (
	"fmt"
	"os"
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

	switch args[1] {
	case "config":
		return runConfig(args[2:])
	case "install":
		return runInstall(args[2:])
	case "db":
		return runDBPublic(args[2:])
	case "_db":
		return runDB(args[2:])
	case "serve":
		return runServe(args[2:])
	case "upgrade":
		return runUpgrade(args[2:])
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
  install           Set up registry (database, certs, user, Quadlet service)
  upgrade           Upgrade registry to a new version
  db version        Print the current database schema version
  config            Configuration tools (validate)
  serve             Start the OCI container registry
  version           Print version information`)
}
