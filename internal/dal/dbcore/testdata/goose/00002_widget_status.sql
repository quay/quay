-- +goose Up
ALTER TABLE widget ADD COLUMN status TEXT NOT NULL DEFAULT 'active';
CREATE INDEX widget_status_idx ON widget (status);

-- +goose Down
DROP INDEX widget_status_idx;
ALTER TABLE widget DROP COLUMN status;
