package cmd

import (
	"bytes"
	"context"
	"flag"
	"strings"
	"testing"
)

func TestCommand_Execute(t *testing.T) {
	tests := []struct {
		name     string
		cmd      func() *Command
		args     []string
		wantCode int
	}{
		{
			name: "dispatches to subcommand",
			cmd: func() *Command {
				return &Command{
					Name: "root",
					Subcommands: []*Command{
						{Name: "sub", Run: func(_ context.Context, _ *Command, _ []string) int { return 0 }},
					},
				}
			},
			args:     []string{"sub"},
			wantCode: 0,
		},
		{
			name: "unknown subcommand returns 1",
			cmd: func() *Command {
				return &Command{
					Name: "root",
					Subcommands: []*Command{
						{Name: "sub", Run: func(_ context.Context, _ *Command, _ []string) int { return 0 }},
					},
				}
			},
			args:     []string{"bogus"},
			wantCode: 1,
		},
		{
			name: "no args no Run returns 1",
			cmd: func() *Command {
				return &Command{
					Name: "root",
					Subcommands: []*Command{
						{Name: "sub", Run: func(_ context.Context, _ *Command, _ []string) int { return 0 }},
					},
				}
			},
			args:     []string{},
			wantCode: 1,
		},
		{
			name: "help literal returns 0",
			cmd: func() *Command {
				return &Command{Name: "root"}
			},
			args:     []string{"help"},
			wantCode: 0,
		},
		{
			name: "dash h returns 0",
			cmd: func() *Command {
				return &Command{Name: "root"}
			},
			args:     []string{"-h"},
			wantCode: 0,
		},
		{
			name: "double dash help returns 0",
			cmd: func() *Command {
				return &Command{Name: "root"}
			},
			args:     []string{"--help"},
			wantCode: 0,
		},
		{
			name: "leaf command parses flags",
			cmd: func() *Command {
				fs := flag.NewFlagSet("leaf", flag.ContinueOnError)
				val := fs.String("name", "", "a name")
				return &Command{
					Name:  "leaf",
					Flags: fs,
					Run: func(_ context.Context, _ *Command, _ []string) int {
						if *val == "alice" {
							return 0
						}
						return 1
					},
				}
			},
			args:     []string{"-name=alice"},
			wantCode: 0,
		},
		{
			name: "run receives remaining positional args",
			cmd: func() *Command {
				fs := flag.NewFlagSet("leaf", flag.ContinueOnError)
				_ = fs.String("name", "", "a name")
				return &Command{
					Name:  "leaf",
					Flags: fs,
					Run: func(_ context.Context, _ *Command, args []string) int {
						if len(args) == 1 && args[0] == "extra" {
							return 0
						}
						return 1
					},
				}
			},
			args:     []string{"-name=alice", "extra"},
			wantCode: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := tt.cmd().Execute(t.Context(), tt.args)
			if got != tt.wantCode {
				t.Errorf("Execute() = %d, want %d", got, tt.wantCode)
			}
		})
	}
}

func TestCommand_FlagPropagation(t *testing.T) {
	t.Run("globals after subcommand", func(t *testing.T) {
		rootFS := flag.NewFlagSet("root", flag.ContinueOnError)
		level := rootFS.String("log-level", "", "log level")

		root := &Command{
			Name:  "root",
			Flags: rootFS,
			Subcommands: []*Command{
				{Name: "sub", Run: func(_ context.Context, _ *Command, _ []string) int {
					if *level == "debug" {
						return 0
					}
					return 1
				}},
			},
		}

		got := root.Execute(t.Context(), []string{"sub", "-log-level=debug"})
		if got != 0 {
			t.Errorf("Execute() = %d, want 0; log-level = %q", got, *level)
		}
	})

	t.Run("globals before subcommand", func(t *testing.T) {
		rootFS := flag.NewFlagSet("root", flag.ContinueOnError)
		level := rootFS.String("log-level", "", "log level")

		root := &Command{
			Name:  "root",
			Flags: rootFS,
			Subcommands: []*Command{
				{Name: "sub", Run: func(_ context.Context, _ *Command, _ []string) int {
					if *level == "debug" {
						return 0
					}
					return 1
				}},
			},
		}

		got := root.Execute(t.Context(), []string{"-log-level=debug", "sub"})
		if got != 0 {
			t.Errorf("Execute() = %d, want 0; log-level = %q", got, *level)
		}
	})

	t.Run("child flag does not clobber parent flag definition", func(t *testing.T) {
		rootFS := flag.NewFlagSet("root", flag.ContinueOnError)
		_ = rootFS.String("shared", "root-default", "")

		childFS := flag.NewFlagSet("child", flag.ContinueOnError)
		childVal := childFS.String("shared", "child-default", "")

		root := &Command{
			Name:  "root",
			Flags: rootFS,
			Subcommands: []*Command{
				{Name: "child", Flags: childFS, Run: func(_ context.Context, _ *Command, _ []string) int {
					if *childVal == "child-default" {
						return 0
					}
					return 1
				}},
			},
		}

		got := root.Execute(t.Context(), []string{"child"})
		if got != 0 {
			t.Errorf("child's own flag was clobbered by propagation")
		}
	})
}

func TestCommand_AfterParse(t *testing.T) {
	t.Run("runs after parse before Run", func(t *testing.T) {
		var order []string

		fs := flag.NewFlagSet("leaf", flag.ContinueOnError)
		_ = fs.String("name", "", "")

		cmd := &Command{
			Name:  "leaf",
			Flags: fs,
			AfterParse: func() error {
				order = append(order, "afterparse")
				return nil
			},
			Run: func(_ context.Context, _ *Command, _ []string) int {
				order = append(order, "run")
				return 0
			},
		}

		cmd.Execute(t.Context(), []string{"-name=x"})
		if len(order) != 2 || order[0] != "afterparse" || order[1] != "run" {
			t.Errorf("order = %v, want [afterparse run]", order)
		}
	})

	t.Run("parent chains onto child", func(t *testing.T) {
		var order []string

		root := &Command{
			Name: "root",
			AfterParse: func() error {
				order = append(order, "parent")
				return nil
			},
			Subcommands: []*Command{
				{
					Name: "child",
					AfterParse: func() error {
						order = append(order, "child")
						return nil
					},
					Run: func(_ context.Context, _ *Command, _ []string) int {
						order = append(order, "run")
						return 0
					},
				},
			},
		}

		root.Execute(t.Context(), []string{"child"})
		if len(order) != 3 || order[0] != "parent" || order[1] != "child" || order[2] != "run" {
			t.Errorf("order = %v, want [parent child run]", order)
		}
	})
}

func TestCommand_NestedSubcommands(t *testing.T) {
	fs := flag.NewFlagSet("validate", flag.ContinueOnError)
	cfg := fs.String("config", "", "config path")

	root := &Command{
		Name: "root",
		Subcommands: []*Command{
			{
				Name: "config",
				Subcommands: []*Command{
					{
						Name:  "validate",
						Flags: fs,
						Run: func(_ context.Context, _ *Command, _ []string) int {
							if *cfg == "foo.yaml" {
								return 0
							}
							return 1
						},
					},
				},
			},
		},
	}

	got := root.Execute(t.Context(), []string{"config", "validate", "-config=foo.yaml"})
	if got != 0 {
		t.Errorf("nested subcommand dispatch failed: got %d", got)
	}
}

func TestCommand_Usage(t *testing.T) {
	fs := flag.NewFlagSet("serve", flag.ContinueOnError)
	fs.String("addr", ":8443", "listen address")

	cmd := &Command{
		Name:        "serve",
		Description: "Start the registry server",
		Flags:       fs,
		Subcommands: []*Command{
			{Name: "sub", Synopsis: "A subcommand"},
		},
	}

	var buf bytes.Buffer
	cmd.Usage(&buf)
	out := buf.String()

	for _, want := range []string{"usage: serve", "Start the registry", "commands:", "sub", "A subcommand", "flags:", "-addr"} {
		if !strings.Contains(out, want) {
			t.Errorf("Usage() missing %q in:\n%s", want, out)
		}
	}
}

func TestCommand_UnknownCommandError(t *testing.T) {
	root := &Command{
		Name: "root",
		Subcommands: []*Command{
			{Name: "valid", Run: func(_ context.Context, _ *Command, _ []string) int { return 0 }},
		},
	}

	// Capture stderr by redirecting FlagSet output
	got := root.Execute(t.Context(), []string{"invalid"})
	if got != 1 {
		t.Errorf("unknown command should return 1, got %d", got)
	}
}
