-- revision: b1a79fa8e630
-- down_revision: c3d4e5f6a7b8

CREATE UNIQUE INDEX user_email_unique_non_org
ON "user" (email)
WHERE organization = false;

DROP INDEX IF EXISTS user_email;

UPDATE "user"
SET email = (
	SELECT contact_email
	FROM organizationcontactemail
	WHERE organization_id = "user".id
		AND contact_email IS NOT NULL
)
WHERE organization = true
	AND email NOT LIKE '%@%'
	AND EXISTS (
		SELECT 1
		FROM organizationcontactemail
		WHERE organization_id = "user".id
			AND contact_email IS NOT NULL
	);

CREATE INDEX user_email_idx ON "user" (email);
