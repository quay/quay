package main

import (
	"fmt"
	"os"
	"time"

	"github.com/quay/quay/openshift-tests-ext/pkg/adapter"
	"github.com/quay/quay/openshift-tests-ext/test/quay"
	"github.com/spf13/cobra"

	"github.com/openshift-eng/openshift-tests-extension/pkg/cmd"
	e "github.com/openshift-eng/openshift-tests-extension/pkg/extension"
)

func main() {
	defaultTimeout := 5 * time.Minute

	registry := e.NewRegistry()
	ext := e.NewExtension("quay", "external", "quay-tests")

	// Add quay/all suite
	ext.AddSuite(e.Suite{
		Name:             "quay/all",
		Description:      "All Quay registry tests",
		Qualifiers:       []string{`tags["component"] == "quay"`},
		ClusterStability: e.ClusterStabilityStable,
		Parallelism:      1,
		TestTimeout:      &defaultTimeout,
	})

	// Add quay/smoke suite
	ext.AddSuite(e.Suite{
		Name:             "quay/smoke",
		Description:      "Quay smoke tests",
		Qualifiers:       []string{`labels.exists(l, l=="SMOKE")`},
		ClusterStability: e.ClusterStabilityStable,
		Parallelism:      1,
		TestTimeout:      &defaultTimeout,
	})

	// Build test specs from Quay scenarios (following Ori's adapter pattern)
	specs, err := adapter.BuildExtensionTestSpecsFromQuayScenarios(quay.QuayScenarios, nil)
	if err != nil {
		panic(fmt.Sprintf("couldn't build extension test specs from Quay scenarios: %+v", err.Error()))
	}

	ext.AddSpecs(specs)
	registry.Register(ext)

	root := &cobra.Command{
		Use:   "quay-tests",
		Short: "Quay Tests Extension for OpenShift",
		Long:  "OpenShift Tests Extension (OTE) binary for Quay registry testing",
	}

	root.AddCommand(cmd.DefaultExtensionCommands(registry)...)

	if err := root.Execute(); err != nil {
		os.Exit(1)
	}
}
