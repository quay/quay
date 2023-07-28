package commands

import (
	"fmt"

	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(versionCmd)
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number of config-tool",
	Long:  `Print the version number of config-tool`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("config-tool v0.1.0")
	},
}
