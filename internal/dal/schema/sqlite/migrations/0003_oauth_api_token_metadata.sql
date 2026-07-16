-- revision: d064a4f00d4a
-- down_revision: b1a79fa8e630

ALTER TABLE oauthaccesstoken ADD COLUMN last_accessed DATETIME;
ALTER TABLE oauthaccesstoken ADD COLUMN created DATETIME;

CREATE INDEX oauthaccesstoken_application_id_last_accessed
ON oauthaccesstoken (application_id, last_accessed);

INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_oauth_api_token');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('revoke_oauth_api_token');
