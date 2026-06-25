// Package main is the entrypoint for the Quay Go CLI.
package main

import (
	"os"

	"github.com/quay/quay/internal/cmd"
)

func main() {
	os.Exit(cmd.Run(os.Args))
}
