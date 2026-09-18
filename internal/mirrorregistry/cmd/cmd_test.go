package cmd

import (
	"bytes"
	"regexp"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// listedCommands returns the names printed in the "commands:" section of
// usage output, ignoring the "flags:" section that follows it.
func listedCommands(t *testing.T, usage string) []string {
	t.Helper()
	_, commands, found := strings.Cut(usage, "commands:\n")
	require.True(t, found, "usage output has no commands section:\n%s", usage)
	commands, _, _ = strings.Cut(commands, "\nflags:")
	matches := regexp.MustCompile(`(?m)^ {2}(\S+)\s`).FindAllStringSubmatch(commands, -1)
	names := make([]string, 0, len(matches))
	for _, match := range matches {
		names = append(names, match[1])
	}
	return names
}

func TestRootUsageHidesInternalCommands(t *testing.T) {
	var buf bytes.Buffer
	newRootCmd().Usage(&buf)

	listed := listedCommands(t, buf.String())
	// Assert membership rather than the exact list so adding an end-user
	// command (for example upgrade) does not turn this into a false failure.
	for _, name := range []string{"install", "uninstall", "config", "migrate", "version"} {
		assert.Contains(t, listed, name)
	}
	assert.NotContains(t, listed, "init")
	assert.NotContains(t, listed, "serve")
}

func TestRootStillDispatchesInternalCommands(t *testing.T) {
	root := newRootCmd()
	for _, name := range []string{"init", "serve"} {
		t.Run(name, func(t *testing.T) {
			sub := root.findSubcommand(name)
			require.NotNil(t, sub, "%s must remain dispatchable for the container entrypoint", name)
			assert.True(t, sub.Hidden)
			assert.Equal(t, 0, root.Execute(t.Context(), []string{name, "-h"}))
		})
	}
}
