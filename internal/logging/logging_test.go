package logging

import (
	"bytes"
	"encoding/json"
	"log/slog"
	"testing"

	"github.com/sirupsen/logrus"
)

func TestSetup_JSON(t *testing.T) {
	var buf bytes.Buffer
	if err := Setup("info", "json", &buf); err != nil {
		t.Fatalf("Setup() error: %v", err)
	}

	if slog.Default().Handler() == nil {
		t.Fatal("slog default handler is nil after Setup")
	}

	logrus.WithField("test", true).Info("bridge test")
}

func TestSetup_Text(t *testing.T) {
	var buf bytes.Buffer
	if err := Setup("debug", "text", &buf); err != nil {
		t.Fatalf("Setup() error: %v", err)
	}
}

func TestSetup_InvalidLevel(t *testing.T) {
	var buf bytes.Buffer
	if err := Setup("bogus", "json", &buf); err == nil {
		t.Error("expected error for invalid level")
	}
}

func TestSetup_InvalidFormat(t *testing.T) {
	var buf bytes.Buffer
	if err := Setup("info", "xml", &buf); err == nil {
		t.Error("expected error for invalid format")
	}
}

func TestSetup_LogrusFlowsThroughSlog(t *testing.T) {
	var buf bytes.Buffer
	if err := Setup("debug", "json", &buf); err != nil {
		t.Fatalf("Setup() error: %v", err)
	}

	logrus.WithField("component", "registry").Info("push complete")

	var record map[string]any
	if err := json.Unmarshal(buf.Bytes(), &record); err != nil {
		t.Fatalf("unmarshal: %v (raw: %s)", err, buf.String())
	}
	if got := record["msg"]; got != "push complete" {
		t.Errorf("msg = %v, want %q", got, "push complete")
	}
	if got := record["component"]; got != "registry" {
		t.Errorf("component = %v, want %q", got, "registry")
	}
}

func TestSetup_Idempotent(t *testing.T) {
	var buf bytes.Buffer
	if err := Setup("info", "json", &buf); err != nil {
		t.Fatalf("first Setup() error: %v", err)
	}
	if err := Setup("debug", "text", &buf); err != nil {
		t.Fatalf("second Setup() error: %v", err)
	}
}

func TestResolveConfig_FlagOverridesAll(t *testing.T) {
	t.Setenv("DEBUGLOG", "true")
	level, format := ResolveConfig("warn", "text", "debug", "json")
	if level != "warn" {
		t.Errorf("level = %q, want %q", level, "warn")
	}
	if format != "text" {
		t.Errorf("format = %q, want %q", format, "text")
	}
}

func TestResolveConfig_ConfigOverridesEnv(t *testing.T) {
	t.Setenv("DEBUGLOG", "true")
	level, format := ResolveConfig("", "", "warn", "text")
	if level != "warn" {
		t.Errorf("level = %q, want %q (config should override env)", level, "warn")
	}
	if format != "text" {
		t.Errorf("format = %q, want %q (config should override env)", format, "text")
	}
}

func TestResolveConfig_EnvOverridesDefaults(t *testing.T) {
	t.Setenv("DEBUGLOG", "true")
	t.Setenv("JSONLOG", "true")
	level, format := ResolveConfig("", "", "", "")
	if level != "debug" {
		t.Errorf("level = %q, want %q (DEBUGLOG=true)", level, "debug")
	}
	if format != "json" {
		t.Errorf("format = %q, want %q (JSONLOG=true)", format, "json")
	}
}

func TestResolveConfig_Defaults(t *testing.T) {
	t.Setenv("DEBUGLOG", "")
	t.Setenv("JSONLOG", "")
	level, format := ResolveConfig("", "", "", "")
	if level != "info" {
		t.Errorf("level = %q, want %q", level, "info")
	}
	if format != "json" {
		t.Errorf("format = %q, want %q", format, "json")
	}
}
