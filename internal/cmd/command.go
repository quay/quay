package cmd

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
)

// Command represents a CLI command or subcommand. It provides dispatch,
// flag parsing, and automatic help generation using only the stdlib flag package.
type Command struct {
	Name        string
	Synopsis    string
	Description string
	Flags       *flag.FlagSet
	Subcommands []*Command
	Run         func(ctx context.Context, cmd *Command, args []string) int
	// AfterParse runs after flag parsing but before Run. Parent hooks are
	// chained onto children by propagateFlags so global setup (e.g. logging)
	// fires at the leaf after all shared flag values are populated.
	AfterParse func() error
}

// Execute dispatches to a subcommand or parses flags and calls Run.
func (c *Command) Execute(ctx context.Context, args []string) int {
	if len(args) > 0 {
		if args[0] == "help" || args[0] == "-h" || args[0] == "--help" {
			c.Usage(os.Stderr)
			return 0
		}
		for _, sub := range c.Subcommands {
			if args[0] == sub.Name {
				c.propagateFlags(sub)
				return sub.Execute(ctx, args[1:])
			}
		}
	}

	if c.Flags != nil {
		c.Flags.SetOutput(os.Stderr)
		if err := c.Flags.Parse(args); err != nil {
			if errors.Is(err, flag.ErrHelp) {
				return 0
			}
			return 1
		}
		args = c.Flags.Args()
	}

	// After parsing, remaining args may start with a subcommand.
	// This handles: quay -log-level=debug serve
	if len(args) > 0 && len(c.Subcommands) > 0 {
		for _, sub := range c.Subcommands {
			if args[0] == sub.Name {
				c.propagateFlags(sub)
				return sub.Execute(ctx, args[1:])
			}
		}
		if c.Run == nil {
			fmt.Fprintf(os.Stderr, "unknown command: %s\n", args[0])
			c.Usage(os.Stderr)
			return 1
		}
	}

	if c.AfterParse != nil {
		if err := c.AfterParse(); err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			return 1
		}
	}

	if c.Run == nil {
		c.Usage(os.Stderr)
		return 1
	}

	return c.Run(ctx, c, args)
}

// propagateFlags registers the parent's flag definitions on the child's
// FlagSet via flag.Var, sharing the same Value pointers. It also chains
// the parent's AfterParse onto the child's.
func (c *Command) propagateFlags(child *Command) {
	if c.Flags != nil {
		if child.Flags == nil {
			child.Flags = flag.NewFlagSet(child.Name, flag.ContinueOnError)
		}
		c.Flags.VisitAll(func(f *flag.Flag) {
			if child.Flags.Lookup(f.Name) == nil {
				child.Flags.Var(f.Value, f.Name, f.Usage)
			}
		})
	}

	if c.AfterParse != nil {
		parentAP := c.AfterParse
		childAP := child.AfterParse
		child.AfterParse = func() error {
			if err := parentAP(); err != nil {
				return err
			}
			if childAP != nil {
				return childAP()
			}
			return nil
		}
	}
}

// Usage writes auto-generated help to w.
func (c *Command) Usage(w io.Writer) {
	fmt.Fprintf(w, "usage: %s", c.Name)
	if len(c.Subcommands) > 0 {
		fmt.Fprint(w, " <command>")
	}
	fmt.Fprintln(w, " [flags]")

	if c.Description != "" {
		fmt.Fprintf(w, "\n%s\n", c.Description)
	}

	if len(c.Subcommands) > 0 {
		fmt.Fprintln(w, "\ncommands:")
		for _, sub := range c.Subcommands {
			fmt.Fprintf(w, "  %-18s %s\n", sub.Name, sub.Synopsis)
		}
	}

	if c.Flags != nil {
		fmt.Fprintln(w, "\nflags:")
		c.Flags.SetOutput(w)
		c.Flags.PrintDefaults()
	}
}
