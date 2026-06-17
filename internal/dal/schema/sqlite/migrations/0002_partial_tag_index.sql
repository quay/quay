-- revision: d4e5f6a7b8c9
DROP INDEX IF EXISTS tag_repository_id_name_lifetime_end_ms;
CREATE UNIQUE INDEX tag_repository_id_name_active ON tag (repository_id, name) WHERE lifetime_end_ms IS NULL;
CREATE INDEX tag_repository_id_name_lifetime_end_ms ON tag (repository_id, name, lifetime_end_ms);
