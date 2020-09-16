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
	"path"

	"github.com/jojomi/go-spew/spew"
	"github.com/quay/config-tool/pkg/lib/config"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

// validateCmd represents the validate command
var printCmd = &cobra.Command{
	Use:   "print",
	Short: "Print your config.yaml to show all values",

	Run: func(cmd *cobra.Command, args []string) {

		// Read config file
		configFilePath := path.Join(configDir, "config.yaml")
		configBytes, err := ioutil.ReadFile(configFilePath)
		if err != nil {
			fmt.Println(err.Error())
			return
		}

		// Load config into struct
		var conf map[string]interface{}
		if err = yaml.Unmarshal(configBytes, &conf); err != nil {
			fmt.Println(err.Error())
			return
		}

		spew.Dump(conf)

		configFieldGroups, err := config.NewConfig(conf)
		if err != nil {
			fmt.Println(err.Error())
			return
		}

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

func init() {

	// Add validation command
	rootCmd.AddCommand(printCmd)

	// Add --config flag
	printCmd.Flags().StringVarP(&configDir, "configDir", "c", "", "The directory containing your config files")
	printCmd.MarkFlagRequired("configDir")

}
