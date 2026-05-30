package logging

import (
	"log/slog"
	"testing"

	"github.com/sirupsen/logrus"
)

func TestParseLevel(t *testing.T) {
	tests := []struct {
		input string
		want  slog.Level
	}{
		{"debug", slog.LevelDebug},
		{"DEBUG", slog.LevelDebug},
		{"info", slog.LevelInfo},
		{"warn", slog.LevelWarn},
		{"error", slog.LevelError},
	}
	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got, err := ParseLevel(tt.input)
			if err != nil {
				t.Fatalf("ParseLevel(%q) error: %v", tt.input, err)
			}
			if got != tt.want {
				t.Errorf("ParseLevel(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestParseLevel_Invalid(t *testing.T) {
	_, err := ParseLevel("bogus")
	if err == nil {
		t.Error("expected error for invalid level")
	}
}

func TestLogrusToSlog(t *testing.T) {
	tests := []struct {
		input logrus.Level
		want  slog.Level
	}{
		{logrus.TraceLevel, slog.LevelDebug - 4},
		{logrus.DebugLevel, slog.LevelDebug},
		{logrus.InfoLevel, slog.LevelInfo},
		{logrus.WarnLevel, slog.LevelWarn},
		{logrus.ErrorLevel, slog.LevelError},
		{logrus.FatalLevel, slog.LevelError + 4},
		{logrus.PanicLevel, slog.LevelError + 8},
	}
	for _, tt := range tests {
		t.Run(tt.input.String(), func(t *testing.T) {
			got := logrusToSlog(tt.input)
			if got != tt.want {
				t.Errorf("logrusToSlog(%v) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}
