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
		configFieldGroups, err := validation.ValidateConf(configPath)
		if err != nil {
			fmt.Println(err.Error())
			return
		}

		// Sort keys
		fgNames := []string{}
		for fgName := range configFieldGroups {
			fgNames = append(fgNames, fgName)
		}
		sort.Strings(fgNames)

		// Initialize validaiton status grid
		validationStatus := [][]string{}

		for _, fgName := range fgNames {

			// Get field group for key
			fieldGroup := configFieldGroups[fgName]

			// Validate
			validationErrors := fieldGroup.Validate()

			// If no errors, append row
			if len(validationErrors) == 0 {
				validationStatus = append(validationStatus, []string{fgName, "-", "🟢"})
			}

			// Append error messages
			for _, err := range validationErrors {

				// Append field group policy violation
				validationStatus = append(validationStatus, []string{fgName, err.Message, "🔴"})
			}
		}

		table := tablewriter.NewWriter(os.Stdout)
		table.SetHeader([]string{"Field Group", "Error", "Status"})
		table.SetBorder(true)
		table.SetAutoFormatHeaders(false)
		table.SetAutoWrapText(false)
		table.AppendBulk(validationStatus)
		table.SetColWidth(1000)
		table.SetRowLine(true)
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
