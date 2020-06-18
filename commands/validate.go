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
	"os"
	"sort"
	"strings"

	"github.com/olekukonko/tablewriter"
	"github.com/quay/config-tool/pkg/lib/validation"
	"github.com/spf13/cobra"
)

// validateCmd represents the validate command
var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate your config.yaml",

	Run: func(cmd *cobra.Command, args []string) {

		// Validate Schema
		configFieldGroups := validation.ValidateConf(configPath)

		// Sort keys
		keys := []string{}
		for key := range configFieldGroups {
			keys = append(keys, key)
		}
		sort.Strings(keys)

		// Initialize validaiton status grid
		validationStatus := [][]string{}

		for _, key := range keys {

			// Get field group for key
			fieldGroup := configFieldGroups[key]

			// Validate
			validationErrors := fieldGroup.Validate()

			// If no errors, append row
			if len(validationErrors) == 0 {
				validationStatus = append(validationStatus, []string{key, "-", "-", "🟢"})
			}

			for _, err := range validationErrors {

				fieldName := removeFieldGroupPrefix(err.Namespace())
				validationStatus = append(validationStatus, []string{key, fieldName, "Field enforces tag: " + err.Tag(), "🔴"})
			}
		}

		table := tablewriter.NewWriter(os.Stdout)
		table.SetHeader([]string{"Field Group", "Field", "Error", "Status"})
		table.SetBorder(true)

		table.AppendBulk(validationStatus)

		table.SetAutoMergeCellsByColumnIndex([]int{0})
		table.Render()

	},
}

func init() {

	// Add validation command
	rootCmd.AddCommand(validateCmd)

	// Add --config flag
	validateCmd.Flags().StringVarP(&configPath, "configPath", "c", "", "The path to a config file")
	validateCmd.MarkFlagRequired("configPath")

}

// removeFieldGroup removes the <fgName>FieldGroup. prefix to a tag name
func removeFieldGroupPrefix(input string) string {
	if i := strings.Index(input, "."); i != -1 {
		return input[i+1:]
	}
	return input
}
