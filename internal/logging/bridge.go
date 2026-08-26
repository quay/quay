package logging

import (
	"context"
	"log/slog"

	"github.com/sirupsen/logrus"
)

type slogFormatter struct {
	handler slog.Handler
}

func (f *slogFormatter) Format(entry *logrus.Entry) ([]byte, error) {
	level := logrusToSlog(entry.Level)
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
