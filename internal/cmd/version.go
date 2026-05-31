package cmd

import (
	"fmt"
	"runtime/debug"
)

// version may be overridden via ldflags for tagged releases:
//
//	go build -ldflags "-X github.com/quay/quay/internal/cmd.version=v1.0.0"
var version = ""

func runVersion() {
	info, ok := debug.ReadBuildInfo()
	if !ok {
		fmt.Println("quay (no build info available)")
		return
	}

	v := version
	if v == "" {
		v = vcsOr(info, "dev")
	}

	fmt.Printf("quay %s\n", v)
	fmt.Printf("  commit:   %s\n", vcsSetting(info, "vcs.revision", "unknown"))
	fmt.Printf("  built:    %s\n", vcsSetting(info, "vcs.time", "unknown"))
	fmt.Printf("  modified: %s\n", vcsSetting(info, "vcs.modified", "unknown"))
	fmt.Printf("  go:       %s\n", info.GoVersion)
}

// vcsOr returns the module version from build info, falling back to def
// when the version is empty or "(devel)".
func vcsOr(info *debug.BuildInfo, def string) string {
	if info.Main.Version != "" && info.Main.Version != "(devel)" {
		return info.Main.Version
	}
	return def
}

func vcsSetting(info *debug.BuildInfo, key, def string) string {
	for _, s := range info.Settings {
		if s.Key == key {
			return s.Value
		}
	}
	return def
}
