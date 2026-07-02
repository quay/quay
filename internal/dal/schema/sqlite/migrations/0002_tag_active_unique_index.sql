-- revision: a2fc72f380b7
-- down_revision: 9fa37f66a9b6

DROP INDEX IF EXISTS tag_repository_id_name_active;
DROP INDEX IF EXISTS tag_repository_id_name_lifetime_end_ms;

CREATE INDEX tag_repository_id_name_lifetime_end_ms
ON tag (repository_id, name, lifetime_end_ms);

UPDATE tag
SET lifetime_end_ms = (
	SELECT kept.lifetime_start_ms
	FROM tag AS kept
	WHERE kept.repository_id = tag.repository_id
		AND kept.name = tag.name
		AND kept.lifetime_end_ms IS NULL
	ORDER BY kept.lifetime_start_ms DESC, kept.id DESC
	LIMIT 1
)
WHERE lifetime_end_ms IS NULL
	AND EXISTS (
		SELECT 1
		FROM tag AS newer
		WHERE newer.repository_id = tag.repository_id
			AND newer.name = tag.name
			AND newer.lifetime_end_ms IS NULL
			AND (
				newer.lifetime_start_ms > tag.lifetime_start_ms
				OR (newer.lifetime_start_ms = tag.lifetime_start_ms AND newer.id > tag.id)
			)
	);

CREATE UNIQUE INDEX tag_repository_id_name_active
ON tag (repository_id, name)
WHERE lifetime_end_ms IS NULL;
