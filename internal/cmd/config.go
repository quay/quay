package cmd

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"

	"github.com/quay/quay/internal/config"
)

func runConfig(args []string) int {
	if len(args) == 0 {
		configUsage()
		return 1
	}

	switch args[0] {
	case "validate":
		return runConfigValidate(args[1:])
	case "help", "-h", "--help":
		configUsage()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown config subcommand: %s\n", args[0])
		configUsage()
		return 1
	}
}

func configUsage() {
	fmt.Fprintln(os.Stderr, `usage: quay config <subcommand> [flags]

subcommands:
  validate          Validate configuration`)
}

// configValidateOpts holds the parsed flags for "quay config validate".
type configValidateOpts struct {
	configPath string
	mode       string
}

// parseConfigValidateFlags parses and validates the flag set for
// "quay config validate". It returns the parsed options, an exit code,
// and whether parsing succeeded. On failure the caller should return
// the exit code without running business logic.
func parseConfigValidateFlags(args []string) (configValidateOpts, int, bool) {
	fs := flag.NewFlagSet("quay config validate", flag.ContinueOnError)

	configPath := fs.String("config", "", "path to config.yaml or config directory")
	mode := fs.String("mode", "offline", "validation mode: offline or online")

	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return configValidateOpts{}, 0, false
		}
		return configValidateOpts{}, 1, false
	}

	if *configPath == "" {
		fmt.Fprintln(os.Stderr, "error: -config flag is required")
		fs.Usage()
		return configValidateOpts{}, 1, false
	}

	if *mode != "offline" && *mode != "online" {
		fmt.Fprintf(os.Stderr, "error: -mode must be \"offline\" or \"online\", got %q\n", *mode)
		return configValidateOpts{}, 1, false
	}

	return configValidateOpts{configPath: *configPath, mode: *mode}, 0, true
}

func runConfigValidate(args []string) int {
	opts, code, ok := parseConfigValidateFlags(args)
	if !ok {
		return code
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	cfg, err := config.Load(opts.configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	valOpts := config.ValidateOptions{Mode: opts.mode}

	if opts.mode == "online" {
		// configPath may be a file path rather than a directory; derive
		// the parent directory so cert loading can walk the config dir.
		configDir := opts.configPath
		info, statErr := os.Stat(configDir)
		if statErr == nil && !info.IsDir() {
			configDir = filepath.Dir(configDir)
		}

		certs, certErr := config.LoadCerts(configDir)
		if certErr != nil {
			fmt.Fprintf(os.Stderr, "error: loading certificates: %v\n", certErr)
			return 1
		}

		pool, poolErr := config.BuildTLSCertPool(certs)
		if poolErr != nil {
			fmt.Fprintf(os.Stderr, "error: building cert pool: %v\n", poolErr)
			return 1
		}

		valOpts.Certificates = certs
		valOpts.CertPool = pool
		valOpts.Probes = config.DefaultProbes(cfg)
	}

	errs := config.Validate(ctx, cfg, valOpts)

	if len(errs) == 0 {
		fmt.Println("Config validation passed.")
		return 0
	}

	errorCount := 0
	for _, e := range errs {
		fmt.Println(e)
		if e.Severity == config.SeverityError {
			errorCount++
		}
	}

	if errorCount > 0 {
		fmt.Fprintf(os.Stderr, "\nConfig validation failed with %d error(s).\n", errorCount)
		return 1
	}

	fmt.Println("\nConfig validation passed with warnings.")
	return 0
}
