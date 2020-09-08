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
	"github.com/quay/config-tool/pkg/lib/editor"
	"github.com/spf13/cobra"
)

var editorPassword string
var operatorEndpoint string

// editorCmd represents the validate command
var editorCmd = &cobra.Command{
	Use:   "editor",
	Short: "Runs a browser-based editor for your config.yaml",

	Run: func(cmd *cobra.Command, args []string) {
		editor.RunConfigEditor(editorPassword, configDir, operatorEndpoint)
	},
}

func init() {
	// Add editor command
	rootCmd.AddCommand(editorCmd)

	// Add --config-dir flag
	editorCmd.Flags().StringVarP(&configDir, "config-dir", "c", "", "The directory containing your config files")
	editorCmd.MarkFlagRequired("config-dir")

	// Add --password flag
	editorCmd.Flags().StringVarP(&editorPassword, "password", "p", "", "The password to enter the editor")
	editorCmd.MarkFlagRequired("password")

	// Add --operator-endpoint flag
	editorCmd.Flags().StringVarP(&operatorEndpoint, "operator-endpoint", "e", "", "The endpoint to commit a validated config bundle to")
	editorCmd.MarkFlagRequired("operator-endpoint")
}
