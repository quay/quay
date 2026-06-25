package logging

import (
	"fmt"
	"log/slog"
	"strings"

	"github.com/sirupsen/logrus"
)

const (
	levelDebug = "debug"
	levelInfo  = "info"
	levelWarn  = "warn"
)

// ParseLevel converts a string log level name to the corresponding slog.Level.
func ParseLevel(s string) (slog.Level, error) {
	switch strings.ToLower(s) {
	case levelDebug:
		return slog.LevelDebug, nil
	case levelInfo:
		return slog.LevelInfo, nil
	case levelWarn, "warning":
		return slog.LevelWarn, nil
	case "error":
		return slog.LevelError, nil
	default:
		return 0, fmt.Errorf("invalid log level %q: must be debug, info, warn, or error", s)
	}
}

func logrusToSlog(level logrus.Level) slog.Level {
	switch level {
	case logrus.TraceLevel:
		return slog.LevelDebug - 4
	case logrus.DebugLevel:
		return slog.LevelDebug
	case logrus.InfoLevel:
		return slog.LevelInfo
	case logrus.WarnLevel:
		return slog.LevelWarn
	case logrus.ErrorLevel:
		return slog.LevelError
	case logrus.FatalLevel:
		return slog.LevelError + 4
	case logrus.PanicLevel:
		return slog.LevelError + 8
	default:
		return slog.LevelInfo
	}
}
