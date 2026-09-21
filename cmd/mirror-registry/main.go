// Package main is the entrypoint for the mirror-registry CLI.
package main

import (
	"os"

	"github.com/quay/quay/internal/mirrorregistry/cmd"
)

func main() {
	os.Exit(cmd.Run(os.Args))
}
