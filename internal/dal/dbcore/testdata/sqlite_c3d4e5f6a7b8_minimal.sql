-- Minimal faithful SQLite schema at Alembic revision c3d4e5f6a7b8.
-- Key table/index definitions were extracted from:
--   git show 2a84552ed^:internal/dal/schema/sqlite/quay_schema.sql
-- That generated schema includes 414c5e2fc487 and c3d4e5f6a7b8, but predates
-- b1a79fa8e630, d064a4f00d4a, and b30800b1d271. Supporting tables are pared
-- down to the columns needed by the bridge SQL and foreign-key validation.

CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
INSERT INTO alembic_version (version_num) VALUES ('c3d4e5f6a7b8');

CREATE TABLE IF NOT EXISTS "user" (
	id INTEGER NOT NULL,
	uuid VARCHAR(36),
	username VARCHAR(255) NOT NULL,
	password_hash VARCHAR(255),
	email VARCHAR(255) NOT NULL,
	verified BOOLEAN NOT NULL,
	stripe_id VARCHAR(255),
	organization BOOLEAN NOT NULL,
	robot BOOLEAN NOT NULL,
	invoice_email BOOLEAN NOT NULL,
	invalid_login_attempts INTEGER DEFAULT '0' NOT NULL,
	last_invalid_login DATETIME NOT NULL,
	removed_tag_expiration_s BIGINT DEFAULT '1209600' NOT NULL,
	enabled BOOLEAN DEFAULT 1 NOT NULL,
	invoice_email_address VARCHAR(255),
	company VARCHAR(255),
	family_name VARCHAR(255),
	given_name VARCHAR(255),
	location VARCHAR(255),
	maximum_queued_builds_count INTEGER,
	creation_date DATETIME,
	last_accessed DATETIME,
	CONSTRAINT pk_user PRIMARY KEY (id)
);
CREATE UNIQUE INDEX user_email ON user (email);
CREATE UNIQUE INDEX user_username ON user (username);

CREATE TABLE organizationcontactemail (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	contact_email VARCHAR(255),
	CONSTRAINT pk_organizationcontactemail PRIMARY KEY (id),
	CONSTRAINT fk_organizationcontactemail_organization_id_user
		FOREIGN KEY(organization_id) REFERENCES user (id)
);
CREATE UNIQUE INDEX organizationcontactemail_organization_id
	ON organizationcontactemail (organization_id);
CREATE INDEX organizationcontactemail_contact_email
	ON organizationcontactemail (contact_email);

CREATE TABLE IF NOT EXISTS "oauthaccesstoken" (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	application_id INTEGER NOT NULL,
	authorized_user_id INTEGER NOT NULL,
	scope VARCHAR(255) NOT NULL,
	token_type VARCHAR(255) NOT NULL,
	expires_at DATETIME NOT NULL,
	data TEXT NOT NULL,
	token_code VARCHAR(255) NOT NULL,
	token_name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_oauthaccesstoken PRIMARY KEY (id),
	CONSTRAINT fk_oauthaccesstoken_authorized_user_id_user
		FOREIGN KEY(authorized_user_id) REFERENCES user (id),
	CONSTRAINT fk_oauthaccesstoken_application_id_oauthapplication
		FOREIGN KEY(application_id) REFERENCES oauthapplication (id)
);
CREATE INDEX oauthaccesstoken_application_id ON oauthaccesstoken (application_id);
CREATE UNIQUE INDEX oauthaccesstoken_token_name ON oauthaccesstoken (token_name);
CREATE INDEX oauthaccesstoken_uuid ON oauthaccesstoken (uuid);
CREATE INDEX oauthaccesstoken_authorized_user_id ON oauthaccesstoken (authorized_user_id);

CREATE TABLE oauthapplication (id INTEGER PRIMARY KEY);
CREATE TABLE logentrykind (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL UNIQUE
);
CREATE TABLE externalnotificationevent (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL UNIQUE
);
CREATE TABLE externalnotificationmethod (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL UNIQUE
);
CREATE TABLE visibility (id INTEGER PRIMARY KEY);
CREATE TABLE repositorykind (id INTEGER PRIMARY KEY);
CREATE TABLE mediatype (id INTEGER PRIMARY KEY);
CREATE TABLE tagkind (id INTEGER PRIMARY KEY);

CREATE TABLE repository (
	id INTEGER PRIMARY KEY,
	namespace_user_id INTEGER NOT NULL,
	visibility_id INTEGER NOT NULL,
	kind_id INTEGER NOT NULL,
	FOREIGN KEY(namespace_user_id) REFERENCES user (id),
	FOREIGN KEY(visibility_id) REFERENCES visibility (id),
	FOREIGN KEY(kind_id) REFERENCES repositorykind (id)
);
CREATE TABLE manifest (
	id INTEGER PRIMARY KEY,
	repository_id INTEGER NOT NULL,
	digest VARCHAR(255) NOT NULL,
	media_type_id INTEGER NOT NULL,
	artifact_type VARCHAR(255),
	artifact_type_backfilled BOOLEAN,
	FOREIGN KEY(repository_id) REFERENCES repository (id),
	FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
CREATE INDEX manifest_repository_id_artifact_type
	ON manifest (repository_id, artifact_type);
CREATE INDEX manifest_artifact_type_backfilled
	ON manifest (artifact_type_backfilled);
CREATE TABLE tag (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_id INTEGER,
	lifetime_start_ms BIGINT NOT NULL,
	lifetime_end_ms BIGINT,
	tag_kind_id INTEGER NOT NULL,
	hidden BOOLEAN DEFAULT 0 NOT NULL,
	immutable BOOLEAN DEFAULT 0 NOT NULL,
	FOREIGN KEY(repository_id) REFERENCES repository (id),
	FOREIGN KEY(manifest_id) REFERENCES manifest (id),
	FOREIGN KEY(tag_kind_id) REFERENCES tagkind (id)
);
CREATE UNIQUE INDEX tag_repository_id_name_lifetime_end_ms
	ON tag (repository_id, name, lifetime_end_ms);
CREATE INDEX tag_repository_id_immutable ON tag (repository_id, immutable);
CREATE INDEX tag_manifest_id_immutable ON tag (manifest_id, immutable);
CREATE INDEX tag_manifest_id_lifetime_end_ms ON tag (manifest_id, lifetime_end_ms);

CREATE TABLE repomirrorconfig (
	id INTEGER PRIMARY KEY,
	repository_id INTEGER,
	skopeo_timeout BIGINT DEFAULT '300' NOT NULL,
	architecture_filter TEXT,
	FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE namespaceautoprunepolicy (
	id INTEGER PRIMARY KEY,
	uuid VARCHAR(36) NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE INDEX namespaceautoprunepolicy_namespace_id
	ON namespaceautoprunepolicy (namespace_id);
CREATE TABLE repositoryautoprunepolicy (
	id INTEGER PRIMARY KEY,
	uuid VARCHAR(36) NOT NULL,
	repository_id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	FOREIGN KEY(namespace_id) REFERENCES user (id),
	FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE INDEX repositoryautoprunepolicy_repository_id
	ON repositoryautoprunepolicy (repository_id);
CREATE TABLE organizationrhskus (
	id INTEGER PRIMARY KEY,
	subscription_id INTEGER NOT NULL,
	org_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	quantity INTEGER,
	FOREIGN KEY(org_id) REFERENCES user (id),
	FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE UNIQUE INDEX organizationrhskus_subscription_id_org_id
	ON organizationrhskus (subscription_id, org_id);
CREATE UNIQUE INDEX organizationrhskus_subscription_id_org_id_user_id
	ON organizationrhskus (subscription_id, org_id, user_id);
CREATE INDEX organizationrhskus_subscription_id
	ON organizationrhskus (subscription_id);

INSERT INTO user (
	id, uuid, username, email, verified, organization, robot, invoice_email,
	invalid_login_attempts, last_invalid_login, removed_tag_expiration_s, enabled
) VALUES
	(1, '00000000-0000-0000-0000-000000000001', 'restored-org',
	 '00000000-0000-0000-0000-000000000001', 1, 1, 0, 0, 0,
	 '2026-01-01 00:00:00', 1209600, 1),
	(2, '00000000-0000-0000-0000-000000000002', 'member',
	 'member@example.com', 1, 0, 0, 0, 0,
	 '2026-01-01 00:00:00', 1209600, 1),
	(3, '00000000-0000-0000-0000-000000000003', 'long-email-org',
	 'organization-contact-address-that-is-definitely-longer-than-sixty-four-characters@example.com',
	 1, 1, 0, 0, 0, '2026-01-01 00:00:00', 1209600, 1),
	(4, '00000000-0000-0000-0000-000000000004', 'placeholder-contact-org',
	 '00000000-0000-0000-0000-000000000004', 1, 1, 0, 0, 0,
	 '2026-01-01 00:00:00', 1209600, 1),
	(5, '00000000-0000-0000-0000-000000000005', 'existing-email-org',
	 'existing@example.com', 1, 1, 0, 0, 0,
	 '2026-01-01 00:00:00', 1209600, 1);

INSERT INTO organizationcontactemail (id, organization_id, contact_email) VALUES
	(1, 1, 'restored@example.com'),
	(2, 4, 'copied-placeholder-without-at-sign'),
	(3, 5, 'replacement@example.com');

INSERT INTO logentrykind (id, name) VALUES
	(140, 'tag_made_immutable_by_policy'),
	(141, 'tags_made_immutable_by_policy');
