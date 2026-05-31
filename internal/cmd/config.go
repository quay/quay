package cmd

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/config"
)

func newConfigCmd() *Command {
	return &Command{
		Name:     "config",
		Synopsis: "Configuration tools (validate)",
		Subcommands: []*Command{
			newConfigValidateCmd(),
		},
	}
}

func newConfigValidateCmd() *Command {
	fs := flag.NewFlagSet("validate", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml or config directory")
	mode := fs.String("mode", "offline", "validation mode: offline or online")

	return &Command{
		Name:     "validate",
		Synopsis: "Validate configuration",
		Flags:    fs,
		Run: func(ctx context.Context, cmd *Command, _ []string) int {
			if *configPath == "" {
				fmt.Fprintln(os.Stderr, "error: -config flag is required")
				cmd.Usage(os.Stderr)
				return 1
			}
			if *mode != "offline" && *mode != "online" {
				fmt.Fprintf(os.Stderr, "error: -mode must be \"offline\" or \"online\", got %q\n", *mode)
				return 1
			}
			return runConfigValidate(ctx, *configPath, *mode)
		},
	}
}

func runConfigValidate(ctx context.Context, configPath, mode string) int {
	cfg, err := config.Load(configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}

	valOpts := config.ValidateOptions{Mode: mode}

	if mode == "online" {
		configDir := configPath
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
