package logging

import (
	"bytes"
	"encoding/json"
	"log/slog"
	"testing"
	"time"

	"github.com/sirupsen/logrus"
)

func TestSlogFormatter_Format(t *testing.T) {
	var buf bytes.Buffer
	handler := slog.NewJSONHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug})
	formatter := &slogFormatter{handler: handler}

	entry := &logrus.Entry{
		Logger:  logrus.StandardLogger(),
		Time:    time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC),
		Level:   logrus.InfoLevel,
		Message: "test message",
		Data: logrus.Fields{
			"http.request.id": "abc-123",
			"component":       "registry",
		},
	}

	out, err := formatter.Format(entry)
	if err != nil {
		t.Fatalf("Format() error: %v", err)
	}
	if len(out) != 0 {
		t.Errorf("Format() returned %d bytes, want 0 (output goes through slog handler)", len(out))
	}

	var record map[string]any
	if err := json.Unmarshal(buf.Bytes(), &record); err != nil {
		t.Fatalf("unmarshal slog output: %v (raw: %s)", err, buf.String())
	}

	if got := record["msg"]; got != "test message" {
		t.Errorf("msg = %v, want %q", got, "test message")
	}
	if got := record["level"]; got != "INFO" {
		t.Errorf("level = %v, want %q", got, "INFO")
	}
	if got := record["http.request.id"]; got != "abc-123" {
		t.Errorf("http.request.id = %v, want %q", got, "abc-123")
	}
}

func TestSlogFormatter_LevelFiltering(t *testing.T) {
	var buf bytes.Buffer
	handler := slog.NewJSONHandler(&buf, &slog.HandlerOptions{Level: slog.LevelWarn})
	formatter := &slogFormatter{handler: handler}

	entry := &logrus.Entry{
		Logger:  logrus.StandardLogger(),
		Time:    time.Now(),
		Level:   logrus.InfoLevel,
		Message: "should be suppressed",
		Data:    logrus.Fields{},
	}

	if _, err := formatter.Format(entry); err != nil {
		t.Fatalf("Format() error: %v", err)
	}

	if buf.Len() != 0 {
		t.Errorf("expected no output for info at warn level, got: %s", buf.String())
	}
}
