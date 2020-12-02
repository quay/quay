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
	"io/ioutil"
	"os"
	"path"
	"sort"
	"strings"
	"sync"

	"github.com/olekukonko/tablewriter"
	"github.com/quay/config-tool/pkg/lib/config"
	"github.com/quay/config-tool/pkg/lib/shared"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

// validateCmd represents the validate command
var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate your config bundle",

	Run: func(cmd *cobra.Command, args []string) {

		isValid := true

		// Read config file
		configFilePath := path.Join(configDir, "config.yaml")
		configBytes, err := ioutil.ReadFile(configFilePath)
		if err != nil {
			fmt.Println(err.Error())
		}

		// Unmarshal from json
		var conf map[string]interface{}
		if err = yaml.Unmarshal(configBytes, &conf); err != nil {
			fmt.Println(err.Error())
		}

		// Clean config
		conf = shared.FixNumbers(conf)
		conf = shared.RemoveNullValues(conf)

		// Load into struct
		configFieldGroups, err := config.NewConfig(conf)
		if err != nil {
			fmt.Println("An error occurred during validation. Process could not marshal config.yaml. This is most likely due to an incorrect type. \nMore info: " + err.Error())
			return
		}

		// Load certs
		certs := shared.LoadCerts(configDir)
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

		// Create wait group
		var wg sync.WaitGroup

		// Initialize validaiton status grid
		validationStatus := [][]string{}

		for _, fgName := range fgNames {

			// Add to wait group
			wg.Add(1)

			// Call func conncurrently
			go func(wg *sync.WaitGroup) {

				// Call done at the end of func
				defer wg.Done()

				// Get field group for key
				fieldGroup := configFieldGroups[fgName]

				// Set options
				opts := shared.Options{
					Mode:         validationMode,
					Certificates: certs,
				}

				// Validate
				validationErrors := fieldGroup.Validate(opts)

				// If no errors, append row
				if len(validationErrors) == 0 {
					validationStatus = append(validationStatus, []string{fgName, "-", "🟢"})
				}

				// Append error messages
				for _, err := range validationErrors {

					// Append field group policy violation
					validationStatus = append(validationStatus, []string{fgName, err.Message, "🔴"})
					isValid = false
				}
			}(&wg)

			// Wait for calls to finish
			wg.Wait()

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

		if !isValid {
			os.Exit(1)
		}

	},
}

func init() {

	// Add validation command
	rootCmd.AddCommand(validateCmd)

	// Add --config flag
	validateCmd.Flags().StringVarP(&configDir, "configDir", "c", "", "A directory containing your config files")
	validateCmd.MarkFlagRequired("configDir")

	validateCmd.Flags().StringVarP(&validationMode, "mode", "m", "", "The mode to validate the config. Must be either online, offline, or testing (for development only)")
	validateCmd.MarkFlagRequired("mode")

}

// removeFieldGroup removes the <fgName>FieldGroup. prefix to a tag name
func removeFieldGroupPrefix(input string) string {
	if i := strings.Index(input, "."); i != -1 {
		return input[i+1:]
	}
	return input
}
