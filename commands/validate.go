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
	"fmt"

	"github.com/quay/config-tool/pkg/lib"
	"github.com/spf13/cobra"
)

// validateCmd represents the validate command
var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate your config.yaml",

	Run: func(cmd *cobra.Command, args []string) {

		// Validate Schema
		if _, err := lib.ValidateSchema(configPath, schemaPath); err != nil {
			fmt.Println(err.Error())
		} else {
			fmt.Println("Config has valid schema")
		}

	},
}

var configPath string
var schemaPath string

func init() {

	// Add validation command
	rootCmd.AddCommand(validateCmd)

	// Add --schema flag
	validateCmd.Flags().StringVarP(&schemaPath, "schemaPath", "s", "", "The path to a schema JSON file")
	validateCmd.MarkFlagRequired("schemaPath")

	// Add --config flag
	validateCmd.Flags().StringVarP(&configPath, "configPath", "c", "", "The path to a config file")
	validateCmd.MarkFlagRequired("configPath")

}
