-- revision: a2fc72f380b7
-- down_revision: 9fa37f66a9b6

DROP INDEX IF EXISTS tag_repository_id_name_active;
DROP INDEX IF EXISTS tag_repository_id_name_lifetime_end_ms;

CREATE INDEX tag_repository_id_name_lifetime_end_ms
ON tag (repository_id, name, lifetime_end_ms);

UPDATE tag AS protection
SET name = CASE
	WHEN EXISTS (
		SELECT 1
		FROM manifest
		WHERE manifest.id = protection.manifest_id
			AND (
				(substr(manifest.digest, 1, 7) = 'sha256:'
					AND length(substr(manifest.digest, 8)) = 64)
				OR (substr(manifest.digest, 1, 7) = 'sha384:'
					AND length(substr(manifest.digest, 8)) = 96)
				OR (substr(manifest.digest, 1, 7) = 'sha512:'
					AND length(substr(manifest.digest, 8)) = 128)
			)
			AND substr(manifest.digest, 8) NOT GLOB '*[^0-9a-fA-F]*'
	) THEN (
		SELECT '$referrer-' || replace(manifest.digest, ':', '-')
		FROM manifest
		WHERE manifest.id = protection.manifest_id
	)
	ELSE '$referrer-$legacy-' || protection.id
END
WHERE protection.hidden = 1
	AND protection.lifetime_end_ms IS NULL
	AND protection.name LIKE '$referrer-%';

-- Keep the most recently inserted active row. IDs are monotonic even when the
-- wall clock moves backward; clamp loser intervals so end never precedes start.
WITH ranked AS MATERIALIZED (
	SELECT
		id,
		row_number() OVER (
			PARTITION BY repository_id, name
			ORDER BY id DESC
		) AS active_rank,
		first_value(lifetime_start_ms) OVER (
			PARTITION BY repository_id, name
			ORDER BY id DESC
		) AS winner_start_ms
	FROM tag
	WHERE lifetime_end_ms IS NULL
)
UPDATE tag
SET lifetime_end_ms = max(tag.lifetime_start_ms, ranked.winner_start_ms)
FROM ranked
WHERE tag.id = ranked.id
	AND ranked.active_rank > 1;

CREATE UNIQUE INDEX tag_repository_id_name_active
ON tag (repository_id, name)
WHERE lifetime_end_ms IS NULL;
