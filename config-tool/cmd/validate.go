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
package cmd

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"

	"github.com/qri-io/jsonschema"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v2"
)

// validateCmd represents the validate command
var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate your config.yaml",

	Run: func(cmd *cobra.Command, args []string) {

		// Read config file
		configBytes, err := ioutil.ReadFile(configPath)
		if err != nil {
			fmt.Println(err)
			return
		}

		// Load config into struct
		c := &interface{}
		if err = yaml.Unmarshal(configBytes, c); err != nil {
			fmt.Println("Cannot unmarshal config.yaml" + err.Error())
		}

		// Read schema file
		schemaBytes, err := ioutil.ReadFile(schemaPath)
		if err != nil {
			fmt.Println(err)
			return
		}

		// Load schema file into struct
		rs := &jsonschema.Schema{}
		if err := json.Unmarshal(schemaBytes, rs); err != nil {
			fmt.Println("unmarshal schema: " + err.Error())
		}

		errs, err := rs.Validate(context.Background(), configBytes)
		if err != nil {
			panic(err)
		}
		if len(errs) > 0 {
			fmt.Println(errs[0].Error())
		}

		fmt.Println(schemaPath)
		fmt.Println(configPath)
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

// FileExists checks if a file exists at the given path
func FileExists(path string) (bool, error) {

	_, err := os.Stat(path)

	if os.IsNotExist(err) {
		return false, nil
	}

	return err == nil, err
}
