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

	"github.com/qri-io/jsonschema"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v2"
)

// validateCmd represents the validate command
var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate your config.yaml",

	Run: func(cmd *cobra.Command, args []string) {

		// Validate Schema
		if _, err := ValidateSchema(configPath, schemaPath); err != nil {
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

// ValidateSchema checks the config file against a JSON Schema Definition
func ValidateSchema(configPath, schemaPath string) (bool, error) {

	// Read config file
	configBytes, err := ioutil.ReadFile(configPath)
	if err != nil {
		return false, err
	}

	// Load config into struct and convert to JSON
	var c interface{}
	if err = yaml.Unmarshal(configBytes, &c); err != nil {
		return false, err
	}
	c = YAMLtoJSON(c)
	config, err := json.Marshal(c)
	if err != nil {
		return false, err
	}

	// Read schema file
	schemaBytes, err := ioutil.ReadFile(schemaPath)
	if err != nil {
		return false, err
	}

	// Load schema file into struct
	rs := &jsonschema.Schema{}
	if err := json.Unmarshal(schemaBytes, rs); err != nil {
		return false, err
	}

	// Validate config against schema and get errors
	errs, err := rs.ValidateBytes(context.Background(), config)
	if err != nil {
		return false, err
	}
	if len(errs) > 0 {
		for i, err := range errs {
			fmt.Println(i, err)
		}
		return false, nil
	}

	// Scheme validation was successful
	return true, nil
}

// YAMLtoJSON converts a YAML struct JSON
func YAMLtoJSON(i interface{}) interface{} {
	switch x := i.(type) {
	case map[interface{}]interface{}:
		m2 := map[string]interface{}{}
		for k, v := range x {
			m2[k.(string)] = YAMLtoJSON(v)
		}
		return m2
	case []interface{}:
		for i, v := range x {
			x[i] = YAMLtoJSON(v)
		}
	}
	return i
}
