// Package cmd implements the quay CLI subcommand dispatch.
package cmd

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/quay/quay/internal/logging"
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

	flagLevel, flagFormat, remaining := extractGlobalFlags(args)
	level, format := logging.ResolveConfig(flagLevel, flagFormat, "", "")

	if err := logging.Setup(level, format, os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	switch remaining[1] {
	case "config":
		return runConfig(ctx, remaining[2:])
	case "install":
		return runInstall(ctx, remaining[2:])
	case "serve":
		return runServe(ctx, remaining[2:])
	case versionLiteral:
		runVersion()
		return 0
	case helpLiteral, "-h", helpFlag:
		usage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", remaining[1])
		usage()
		return 1
	}
}

func extractGlobalFlags(args []string) (level, format string, remaining []string) {
	remaining = make([]string, 0, len(args))
	remaining = append(remaining, args[0])

	i := 1
	for i < len(args) {
		arg := args[i]
		switch {
		case strings.HasPrefix(arg, "--log-level="):
			level = strings.TrimPrefix(arg, "--log-level=")
		case arg == "--log-level" && i+1 < len(args):
			i++
			level = args[i]
		case strings.HasPrefix(arg, "--log-format="):
			format = strings.TrimPrefix(arg, "--log-format=")
		case arg == "--log-format" && i+1 < len(args):
			i++
			format = args[i]
		default:
			remaining = append(remaining, arg)
		}
		i++
	}
	return level, format, remaining
}

func usage() {
	fmt.Fprintln(os.Stderr, `usage: quay [--log-level=LEVEL] [--log-format=FORMAT] <command> [flags]

global flags:
  --log-level   Log level: debug, info, warn, error (default: info)
  --log-format  Log format: json, text (default: json)

commands:
  install           Set up or upgrade registry (Quadlet service)
  config            Configuration tools (validate)
  serve             Start the OCI container registry
  version           Print version information`)
}
