-- +goose Up
CREATE TABLE widget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE widget_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    widget_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT (datetime('now'))
);

-- A trigger body is one logical CREATE TRIGGER statement that contains
-- multiple internal semicolon-terminated statements. StatementBegin/End
-- tells goose's SQL parser to treat everything between the markers as a
-- single statement instead of splitting on each internal semicolon.
-- +goose StatementBegin
CREATE TRIGGER widget_audit_insert AFTER INSERT ON widget
BEGIN
    INSERT INTO widget_audit (widget_id, action) VALUES (NEW.id, 'insert');
    UPDATE widget SET updated_at = datetime('now') WHERE id = NEW.id;
END;
-- +goose StatementEnd

-- +goose Down
DROP TRIGGER widget_audit_insert;
DROP TABLE widget_audit;
DROP TABLE widget;
