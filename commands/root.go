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

	"github.com/spf13/cobra"
)

var cfgFile string
var configDir string
var validationMode string

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "config-tool",
	Short: "A Configuration Validation Tool for Quay",
	Long:  `This tool allows Quay users to validate their configuration bundles.`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {

	// Persistent Flags
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.config-tool.yaml)")

	//  Local Flags
	rootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}
