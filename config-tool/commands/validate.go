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
	"io/ioutil"
	"os"
	"path"
	"sort"
	"strings"

	"github.com/olekukonko/tablewriter"
	"github.com/quay/config-tool/pkg/lib/config"
	"github.com/quay/config-tool/pkg/lib/shared"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

// validateCmd represents the validate command
var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate your config bundle",

	Run: func(cmd *cobra.Command, args []string) {

		log.SetOutput(os.Stdout)

		// Only log the warning severity or above.
		if os.Getenv("DEBUGLOG") == "true" {
			log.SetLevel(log.DebugLevel)
		} else {
			log.SetLevel(log.WarnLevel)
		}

		isValid := true

		// Read config file
		configFilePath := path.Join(configDir, "config.yaml")
		configBytes, err := ioutil.ReadFile(configFilePath)
		if err != nil {
			log.Fatalf(err.Error())
		}

		// Unmarshal from json
		var conf map[string]interface{}
		if err = yaml.Unmarshal(configBytes, &conf); err != nil {
			log.Fatalf(err.Error())
		}

		// Clean config
		conf = shared.RemoveNullValues(conf)

		// Load into struct
		configFieldGroups, err := config.NewConfig(conf)
		if err != nil {
			log.Fatalf("An error occurred during validation. Process could not marshal config.yaml. This is most likely due to an incorrect type. \nMore info: " + err.Error())
		}

		// Load certs
		certs := shared.LoadCerts(configDir)
		if err != nil {
			log.Fatalf(err.Error())
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

			// Set options
			opts := shared.Options{
				Mode:         validationMode,
				Certificates: certs,
			}

			// Validate
			log.Debugf("Validating %s", fgName)
			validationErrors := fieldGroup.Validate(opts)

			// If no errors, append row
			if len(validationErrors) == 0 {
				validationStatus = append(validationStatus, []string{fgName, "-", "🟢"})
			}

			// Append error messages
			for _, err := range validationErrors {

				log.Debugf(err.FieldGroup, err.Message, err.Tags)

				// Append field group policy violation
				validationStatus = append(validationStatus, []string{fgName, err.Message, "🔴"})
				isValid = false
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
