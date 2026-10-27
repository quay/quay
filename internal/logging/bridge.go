package logging

import (
	"context"
	"log/slog"
	"strconv"

	"github.com/sirupsen/logrus"
)

// responseErrorMessage is the message docker/distribution logs, at ERROR, for
// every response that carried an error code, including routine 4xx answers
// such as the blob-existence HEAD before an upload or a cosign ".sig" tag probe.
const responseErrorMessage = "response completed with error"

// responseStatusField is the logrus field docker/distribution attaches with
// the HTTP status of the completed response.
const responseStatusField = "http.response.status"

type slogFormatter struct {
	handler slog.Handler
}

func (f *slogFormatter) Format(entry *logrus.Entry) ([]byte, error) {
	level := responseErrorLevel(entry, logrusToSlog(entry.Level))
	if !f.handler.Enabled(context.Background(), level) {
		return nil, nil
	}

	record := slog.NewRecord(entry.Time, level, entry.Message, 0)
	for k, v := range entry.Data {
		record.AddAttrs(slog.Any(k, v))
	}

	if err := f.handler.Handle(context.Background(), record); err != nil {
		return nil, err
	}
	return nil, nil
}

// responseErrorLevel demotes docker/distribution's "response completed with
// error" entries when the response status shows the client, not the registry,
// caused the error. A 404 is the normal answer to a blob or manifest existence
// probe and is logged at INFO, the same level as the access log line for a
// successful request, so the request and its status stay visible without
// looking like a failure. Other 4xx responses are logged at WARN. 5xx
// responses, and entries without a recognizable status, keep their level.
// This entry is the only per-request line that carries the status for error
// responses, which is why 404 is not pushed down to DEBUG.
func responseErrorLevel(entry *logrus.Entry, level slog.Level) slog.Level {
	if entry.Message != responseErrorMessage || level < slog.LevelError {
		return level
	}
	status, ok := responseStatus(entry.Data[responseStatusField])
	if !ok || status < 400 || status >= 500 {
		return level
	}
	if status == 404 {
		return slog.LevelInfo
	}
	return slog.LevelWarn
}

func responseStatus(v any) (int, bool) {
	switch s := v.(type) {
	case int:
		return s, true
	case int32:
		return int(s), true
	case int64:
		return int(s), true
	case uint:
		return int(s), true
	case float64:
		return int(s), true
	case string:
		n, err := strconv.Atoi(s)
		return n, err == nil
	default:
		return 0, false
	}
}
