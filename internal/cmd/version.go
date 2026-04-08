package cmd

import "fmt"

// Set via ldflags at build time:
//
//	go build -ldflags "-X github.com/quay/quay/internal/cmd.version=v1.0.0"
var (
	version = "dev"
	commit  = "none"
	date    = "unknown"
)

func runVersion() int {
	fmt.Printf("quay %s (commit: %s, built: %s)\n", version, commit, date)
	return 0
}
