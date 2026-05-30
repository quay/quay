package logging

import (
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/sirupsen/logrus"
)

// Setup configures slog as the default logger and installs the logrus
// formatter bridge. It is idempotent — call it again to reconfigure
// (e.g. after loading config.yaml).
func Setup(level, format string, w io.Writer) error {
	handler, err := newHandler(level, format, w)
	if err != nil {
		return err
	}
	slog.SetDefault(slog.New(handler))
	installBridge(handler)
	return nil
}

// ResolveConfig returns the effective log level and format by applying the
// precedence chain: CLI flags > config.yaml > env vars > defaults.
func ResolveConfig(flagLevel, flagFormat, cfgLevel, cfgFormat string) (string, string) {
	level := resolveValue(flagLevel, cfgLevel, envLevel(), "info")
	format := resolveValue(flagFormat, cfgFormat, envFormat(), "json")
	return level, format
}

func resolveValue(flag, cfg, env, fallback string) string {
	if flag != "" {
		return flag
	}
	if cfg != "" {
		return cfg
	}
	if env != "" {
		return env
	}
	return fallback
}

func envLevel() string {
	if strings.EqualFold(os.Getenv("DEBUGLOG"), "true") {
		return "debug"
	}
	return ""
}

func envFormat() string {
	if strings.EqualFold(os.Getenv("JSONLOG"), "true") {
		return "json"
	}
	return ""
}

func newHandler(level, format string, w io.Writer) (slog.Handler, error) {
	lvl, err := ParseLevel(level)
	if err != nil {
		return nil, err
	}
	opts := &slog.HandlerOptions{Level: lvl}

	switch strings.ToLower(format) {
	case "json":
		return slog.NewJSONHandler(w, opts), nil
	case "text":
		return slog.NewTextHandler(w, opts), nil
	default:
		return nil, fmt.Errorf("invalid log format %q: must be json or text", format)
	}
}

func installBridge(handler slog.Handler) {
	logrus.SetFormatter(&slogFormatter{handler: handler})
	logrus.SetOutput(io.Discard)
	// Let slog control level filtering, not logrus.
	logrus.SetLevel(logrus.TraceLevel)
}
