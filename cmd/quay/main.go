// Package main is the entrypoint for the Quay Go CLI.
package main

import (
	"os"

	"github.com/quay/quay/internal/mirrorregistry/cmd"
)

func main() {
	os.Exit(cmd.Run(os.Args))
}
