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

// TestSlogFormatter_ResponseErrorLevel covers PROJQUAY-13203: the
// docker/distribution "response completed with error" entry is emitted at
// ERROR for every error-coded response, including the 404 a client gets when
// it probes for a blob or manifest before pushing. Client-caused 4xx entries
// are demoted (404 to INFO, other 4xx to WARN); server errors and unrelated
// messages keep their level.
func TestSlogFormatter_ResponseErrorLevel(t *testing.T) {
	tests := []struct {
		name    string
		message string
		level   logrus.Level
		status  any
		want    string
	}{
		{name: "404 blob probe is info", message: responseErrorMessage, level: logrus.ErrorLevel, status: 404, want: "INFO"},
		{name: "404 as int64", message: responseErrorMessage, level: logrus.ErrorLevel, status: int64(404), want: "INFO"},
		{name: "404 as string", message: responseErrorMessage, level: logrus.ErrorLevel, status: "404", want: "INFO"},
		{name: "401 is warn", message: responseErrorMessage, level: logrus.ErrorLevel, status: 401, want: "WARN"},
		{name: "400 is warn", message: responseErrorMessage, level: logrus.ErrorLevel, status: 400, want: "WARN"},
		{name: "500 stays error", message: responseErrorMessage, level: logrus.ErrorLevel, status: 500, want: "ERROR"},
		{name: "missing status stays error", message: responseErrorMessage, level: logrus.ErrorLevel, status: nil, want: "ERROR"},
		{name: "unparseable status stays error", message: responseErrorMessage, level: logrus.ErrorLevel, status: "n/a", want: "ERROR"},
		{name: "other message with 404 stays error", message: "metadata write failed", level: logrus.ErrorLevel, status: 404, want: "ERROR"},
		{name: "already warn is untouched", message: responseErrorMessage, level: logrus.WarnLevel, status: 404, want: "WARN"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			var buf bytes.Buffer
			handler := slog.NewJSONHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug})
			formatter := &slogFormatter{handler: handler}

			data := logrus.Fields{"err.code": "blob unknown", "http.request.method": "HEAD"}
			if tc.status != nil {
				data[responseStatusField] = tc.status
			}
			entry := &logrus.Entry{
				Logger:  logrus.StandardLogger(),
				Time:    time.Now(),
				Level:   tc.level,
				Message: tc.message,
				Data:    data,
			}
			if _, err := formatter.Format(entry); err != nil {
				t.Fatalf("Format() error: %v", err)
			}

			var record map[string]any
			if err := json.Unmarshal(buf.Bytes(), &record); err != nil {
				t.Fatalf("unmarshal slog output: %v (raw: %s)", err, buf.String())
			}
			if got := record["level"]; got != tc.want {
				t.Errorf("level = %v, want %q", got, tc.want)
			}
			if got := record["msg"]; got != tc.message {
				t.Errorf("msg = %v, want %q", got, tc.message)
			}
			if tc.status != nil {
				if _, ok := record[responseStatusField]; !ok {
					t.Errorf("record dropped %s field", responseStatusField)
				}
			}
		})
	}
}

// TestSlogFormatter_DemotedEntryRespectsHandlerLevel verifies a demoted 404
// entry is still filtered by the handler level like any other INFO record, so
// a WARN-level configuration no longer shows client probes at all.
func TestSlogFormatter_DemotedEntryRespectsHandlerLevel(t *testing.T) {
	var buf bytes.Buffer
	handler := slog.NewJSONHandler(&buf, &slog.HandlerOptions{Level: slog.LevelWarn})
	formatter := &slogFormatter{handler: handler}

	entry := &logrus.Entry{
		Logger:  logrus.StandardLogger(),
		Time:    time.Now(),
		Level:   logrus.ErrorLevel,
		Message: responseErrorMessage,
		Data:    logrus.Fields{responseStatusField: 404},
	}
	if _, err := formatter.Format(entry); err != nil {
		t.Fatalf("Format() error: %v", err)
	}
	if buf.Len() != 0 {
		t.Errorf("demoted 404 entry was emitted at WARN handler level: %s", buf.String())
	}
}
