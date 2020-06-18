/*
Copyright © 2020 NAME HERE <EMAIL ADDRESS>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
package commands

import (
	"github.com/jojomi/go-spew/spew"
	"github.com/quay/config-tool/pkg/lib/validation"
	"github.com/spf13/cobra"
)

// validateCmd represents the validate command
var printCmd = &cobra.Command{
	Use:   "print",
	Short: "Print your config.yaml to show all values",

	Run: func(cmd *cobra.Command, args []string) {

		// Validate Schema
		configFieldGroups := validation.ValidateConf(configPath)

		spew.Config.Indent = "\t"
		spew.Config.DisableCapacities = true
		spew.Config.DisablePointerAddresses = true
		spew.Config.SortKeys = true
		spew.Config.DisableMethods = true
		spew.Config.DisableTypes = true
		spew.Config.DisableLengths = true
		spew.Dump(configFieldGroups)

	},
}

var configPath string

func init() {

	// Add validation command
	rootCmd.AddCommand(printCmd)

	// Add --config flag
	printCmd.Flags().StringVarP(&configPath, "configPath", "c", "", "The path to a config file")
	printCmd.MarkFlagRequired("configPath")

}
