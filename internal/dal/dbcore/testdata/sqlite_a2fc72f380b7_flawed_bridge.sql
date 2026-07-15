-- Minimal SQLite fixture captured from the flawed a2fc72f380b7 Go bridge output.
-- Generation provenance:
--   1. Load sqlite_c3d4e5f6a7b8_minimal.sql, extracted from 2a84552ed^.
--   2. Apply bridgeColumns, bridgeIndexFixes, and 0001_bridge_from_omr.sql
--      exactly as committed at pre-fix 12eab99ec.
--   3. Apply 0002_tag_active_unique_index.sql from 12eab99ec and stamp
--      a2fc72f380b7.
-- This is captured migration output, not current DDL with an old version stamp.

CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
CREATE TABLE externalnotificationevent (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL UNIQUE
);
CREATE TABLE externalnotificationmethod (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL UNIQUE
);
CREATE TABLE logentrykind (
	id INTEGER PRIMARY KEY,
	name VARCHAR(255) NOT NULL UNIQUE
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
CREATE TABLE manifestpullstatistics (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_digest VARCHAR(255) NOT NULL,
	manifest_pull_count BIGINT NOT NULL,
	last_manifest_pull_date DATETIME NOT NULL,
	CONSTRAINT pk_manifestpullstatistics PRIMARY KEY (id),
	CONSTRAINT fk_manifestpullstatistics_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE mediatype (id INTEGER PRIMARY KEY);
CREATE TABLE namespaceautoprunepolicy (
	id INTEGER PRIMARY KEY,
	uuid VARCHAR(36) NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE namespaceimmutabilitypolicy (
	id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	CONSTRAINT pk_namespaceimmutabilitypolicyid PRIMARY KEY (id),
	CONSTRAINT fk_namespaceimmutabilitypolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE namespacenotification (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	namespace_id INTEGER NOT NULL,
	event_id INTEGER NOT NULL,
	method_id INTEGER NOT NULL,
	title VARCHAR(255),
	config_json TEXT NOT NULL,
	event_config_json TEXT DEFAULT '{}' NOT NULL,
	number_of_failures INTEGER DEFAULT '0' NOT NULL,
	last_ran_ms BIGINT,
	CONSTRAINT pk_namespacenotification PRIMARY KEY (id),
	CONSTRAINT fk_namespacenotification_namespace_id FOREIGN KEY(namespace_id) REFERENCES user (id),
	CONSTRAINT fk_namespacenotification_event_id FOREIGN KEY(event_id) REFERENCES externalnotificationevent (id),
	CONSTRAINT fk_namespacenotification_method_id FOREIGN KEY(method_id) REFERENCES externalnotificationmethod (id)
);
CREATE TABLE "oauthaccesstoken" (
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
CREATE TABLE oauthapplication (id INTEGER PRIMARY KEY);
CREATE TABLE organizationcontactemail (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	contact_email VARCHAR(255),
	CONSTRAINT pk_organizationcontactemail PRIMARY KEY (id),
	CONSTRAINT fk_organizationcontactemail_organization_id_user
		FOREIGN KEY(organization_id) REFERENCES user (id)
);
CREATE TABLE organizationrhskus (
	id INTEGER PRIMARY KEY,
	subscription_id INTEGER NOT NULL,
	org_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	quantity INTEGER,
	FOREIGN KEY(org_id) REFERENCES user (id),
	FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE orgmirrorconfig (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	creation_date DATETIME NOT NULL,
	is_enabled BOOLEAN DEFAULT (1) NOT NULL,
	mirror_type INTEGER DEFAULT '1' NOT NULL,
	external_registry_type INTEGER NOT NULL,
	external_registry_url VARCHAR(2048) NOT NULL,
	external_namespace VARCHAR(255) NOT NULL,
	external_registry_username VARCHAR(4096),
	external_registry_password VARCHAR(9000),
	external_registry_config TEXT NOT NULL,
	internal_robot_id INTEGER NOT NULL,
	repository_filters TEXT NOT NULL,
	visibility_id INTEGER NOT NULL,
	delete_stale_repos BOOLEAN DEFAULT (0) NOT NULL,
	sync_interval INTEGER NOT NULL,
	sync_start_date DATETIME,
	sync_expiration_date DATETIME,
	sync_retries_remaining INTEGER DEFAULT '3' NOT NULL,
	sync_status INTEGER DEFAULT '0' NOT NULL,
	sync_transaction_id VARCHAR(36),
	skopeo_timeout BIGINT DEFAULT '300' NOT NULL,
	architecture_filter TEXT DEFAULT '[]' NOT NULL,
	CONSTRAINT pk_orgmirrorconfig PRIMARY KEY (id),
	CONSTRAINT fk_orgmirrorconfig_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id),
	CONSTRAINT fk_orgmirrorconfig_internal_robot_id_user FOREIGN KEY(internal_robot_id) REFERENCES user (id),
	CONSTRAINT fk_orgmirrorconfig_visibility_id_visibility FOREIGN KEY(visibility_id) REFERENCES visibility (id)
);
CREATE TABLE orgmirrorrepository (
	id INTEGER NOT NULL,
	org_mirror_config_id INTEGER NOT NULL,
	repository_name VARCHAR(255) NOT NULL,
	repository_id INTEGER,
	discovery_date DATETIME NOT NULL,
	sync_status INTEGER DEFAULT '0' NOT NULL,
	sync_start_date DATETIME,
	sync_expiration_date DATETIME,
	last_sync_date DATETIME,
	status_message TEXT,
	creation_date DATETIME NOT NULL,
	sync_retries_remaining INTEGER DEFAULT '3' NOT NULL,
	sync_transaction_id VARCHAR(36),
	CONSTRAINT pk_orgmirrorrepository PRIMARY KEY (id),
	CONSTRAINT fk_orgmirrorrepository_org_mirror_config_id_orgmirrorconfig FOREIGN KEY(org_mirror_config_id) REFERENCES orgmirrorconfig (id),
	CONSTRAINT fk_orgmirrorrepository_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE quotanotificationstate (
	id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	threshold_percent INTEGER NOT NULL,
	last_notified_at DATETIME,
	cleared BOOLEAN DEFAULT (1) NOT NULL,
	CONSTRAINT pk_quotanotificationstate PRIMARY KEY (id),
	CONSTRAINT fk_quotanotificationstate_namespace_id FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE repomirrorconfig (
	id INTEGER PRIMARY KEY,
	repository_id INTEGER,
	skopeo_timeout BIGINT DEFAULT '300' NOT NULL,
	architecture_filter TEXT,
	FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE repository (
	id INTEGER PRIMARY KEY,
	namespace_user_id INTEGER NOT NULL,
	visibility_id INTEGER NOT NULL,
	kind_id INTEGER NOT NULL,
	FOREIGN KEY(namespace_user_id) REFERENCES user (id),
	FOREIGN KEY(visibility_id) REFERENCES visibility (id),
	FOREIGN KEY(kind_id) REFERENCES repositorykind (id)
);
CREATE TABLE repositoryautoprunepolicy (
	id INTEGER PRIMARY KEY,
	uuid VARCHAR(36) NOT NULL,
	repository_id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	FOREIGN KEY(namespace_id) REFERENCES user (id),
	FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE repositoryimmutabilitypolicy (
	id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	repository_id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	CONSTRAINT pk_repositoryimmutabilitypolicyid PRIMARY KEY (id),
	CONSTRAINT fk_repositoryimmutabilitypolicy_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repositoryimmutabilitypolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE repositorykind (id INTEGER PRIMARY KEY);
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
CREATE TABLE tagkind (id INTEGER PRIMARY KEY);
CREATE TABLE tagpullstatistics (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	tag_name VARCHAR(255) NOT NULL,
	tag_pull_count BIGINT NOT NULL,
	last_tag_pull_date DATETIME NOT NULL,
	current_manifest_digest VARCHAR(255),
	CONSTRAINT pk_tagpullstatistics PRIMARY KEY (id),
	CONSTRAINT fk_tagpullstatistics_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE "user" (
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
CREATE TABLE visibility (id INTEGER PRIMARY KEY);

CREATE INDEX manifest_artifact_type_backfilled
	ON manifest (artifact_type_backfilled);
CREATE INDEX manifest_repository_id_artifact_type
	ON manifest (repository_id, artifact_type);
CREATE UNIQUE INDEX manifestpullstatistics_repository_id_manifest_digest ON manifestpullstatistics (repository_id, manifest_digest);
CREATE INDEX namespaceautoprunepolicy_namespace_id
	ON namespaceautoprunepolicy (namespace_id);
CREATE INDEX namespaceimmutabilitypolicy_namespace_id ON namespaceimmutabilitypolicy (namespace_id);
CREATE UNIQUE INDEX namespaceimmutabilitypolicy_uuid ON namespaceimmutabilitypolicy (uuid);
CREATE INDEX namespacenotification_namespace_id ON namespacenotification (namespace_id);
CREATE INDEX namespacenotification_uuid ON namespacenotification (uuid);
CREATE INDEX oauthaccesstoken_application_id ON oauthaccesstoken (application_id);
CREATE INDEX oauthaccesstoken_authorized_user_id ON oauthaccesstoken (authorized_user_id);
CREATE UNIQUE INDEX oauthaccesstoken_token_name ON oauthaccesstoken (token_name);
CREATE INDEX oauthaccesstoken_uuid ON oauthaccesstoken (uuid);
CREATE INDEX organizationcontactemail_contact_email
	ON organizationcontactemail (contact_email);
CREATE UNIQUE INDEX organizationcontactemail_organization_id
	ON organizationcontactemail (organization_id);
CREATE INDEX organizationrhskus_subscription_id
	ON organizationrhskus (subscription_id);
CREATE UNIQUE INDEX organizationrhskus_subscription_id_org_id
	ON organizationrhskus (subscription_id, org_id);
CREATE UNIQUE INDEX organizationrhskus_subscription_id_org_id_user_id
	ON organizationrhskus (subscription_id, org_id, user_id);
CREATE INDEX orgmirrorconfig_internal_robot_id ON orgmirrorconfig (internal_robot_id);
CREATE UNIQUE INDEX orgmirrorconfig_organization_id ON orgmirrorconfig (organization_id);
CREATE INDEX orgmirrorconfig_sync_start_date ON orgmirrorconfig (sync_start_date);
CREATE INDEX orgmirrorconfig_sync_status ON orgmirrorconfig (sync_status);
CREATE UNIQUE INDEX orgmirrorrepository_config_repo_name ON orgmirrorrepository (org_mirror_config_id, repository_name);
CREATE INDEX orgmirrorrepository_config_status ON orgmirrorrepository (org_mirror_config_id, sync_status);
CREATE INDEX orgmirrorrepository_org_mirror_config_id ON orgmirrorrepository (org_mirror_config_id);
CREATE INDEX orgmirrorrepository_repository_id ON orgmirrorrepository (repository_id);
CREATE INDEX orgmirrorrepository_sync_status ON orgmirrorrepository (sync_status);
CREATE INDEX quotanotificationstate_namespace_id ON quotanotificationstate (namespace_id);
CREATE UNIQUE INDEX quotanotificationstate_namespace_threshold ON quotanotificationstate (namespace_id, threshold_percent);
CREATE INDEX repositoryautoprunepolicy_repository_id
	ON repositoryautoprunepolicy (repository_id);
CREATE INDEX repositoryimmutabilitypolicy_namespace_id ON repositoryimmutabilitypolicy (namespace_id);
CREATE INDEX repositoryimmutabilitypolicy_repository_id ON repositoryimmutabilitypolicy (repository_id);
CREATE UNIQUE INDEX repositoryimmutabilitypolicy_uuid ON repositoryimmutabilitypolicy (uuid);
CREATE INDEX tag_manifest_id_immutable ON tag (manifest_id, immutable);
CREATE INDEX tag_manifest_id_lifetime_end_ms ON tag (manifest_id, lifetime_end_ms);
CREATE INDEX tag_repository_id_immutable ON tag (repository_id, immutable);
CREATE UNIQUE INDEX tag_repository_id_name_active
ON tag (repository_id, name)
WHERE lifetime_end_ms IS NULL;
CREATE INDEX tag_repository_id_name_lifetime_end_ms
ON tag (repository_id, name, lifetime_end_ms);
CREATE UNIQUE INDEX tagpullstatistics_repository_id_tag_name ON tagpullstatistics (repository_id, tag_name);
CREATE UNIQUE INDEX user_email ON user (email);
CREATE UNIQUE INDEX user_username ON user (username);

INSERT INTO "alembic_version" ("version_num") VALUES ('a2fc72f380b7');

INSERT INTO "user" ("id", "uuid", "username", "password_hash", "email", "verified", "stripe_id", "organization", "robot", "invoice_email", "invalid_login_attempts", "last_invalid_login", "removed_tag_expiration_s", "enabled", "invoice_email_address", "company", "family_name", "given_name", "location", "maximum_queued_builds_count", "creation_date", "last_accessed") VALUES (1, '00000000-0000-0000-0000-000000000001', 'restored-org', NULL, '00000000-0000-0000-0000-000000000001', 1, NULL, 1, 0, 0, 0, '2026-01-01 00:00:00 +0000 UTC', 1209600, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "user" ("id", "uuid", "username", "password_hash", "email", "verified", "stripe_id", "organization", "robot", "invoice_email", "invalid_login_attempts", "last_invalid_login", "removed_tag_expiration_s", "enabled", "invoice_email_address", "company", "family_name", "given_name", "location", "maximum_queued_builds_count", "creation_date", "last_accessed") VALUES (2, '00000000-0000-0000-0000-000000000002', 'member', NULL, 'member@example.com', 1, NULL, 0, 0, 0, 0, '2026-01-01 00:00:00 +0000 UTC', 1209600, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "user" ("id", "uuid", "username", "password_hash", "email", "verified", "stripe_id", "organization", "robot", "invoice_email", "invalid_login_attempts", "last_invalid_login", "removed_tag_expiration_s", "enabled", "invoice_email_address", "company", "family_name", "given_name", "location", "maximum_queued_builds_count", "creation_date", "last_accessed") VALUES (3, '00000000-0000-0000-0000-000000000003', 'long-email-org', NULL, 'organization-contact-address-that-is-definitely-longer-than-sixty-four-characters@example.com', 1, NULL, 1, 0, 0, 0, '2026-01-01 00:00:00 +0000 UTC', 1209600, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "user" ("id", "uuid", "username", "password_hash", "email", "verified", "stripe_id", "organization", "robot", "invoice_email", "invalid_login_attempts", "last_invalid_login", "removed_tag_expiration_s", "enabled", "invoice_email_address", "company", "family_name", "given_name", "location", "maximum_queued_builds_count", "creation_date", "last_accessed") VALUES (4, '00000000-0000-0000-0000-000000000004', 'placeholder-contact-org', NULL, '00000000-0000-0000-0000-000000000004', 1, NULL, 1, 0, 0, 0, '2026-01-01 00:00:00 +0000 UTC', 1209600, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "user" ("id", "uuid", "username", "password_hash", "email", "verified", "stripe_id", "organization", "robot", "invoice_email", "invalid_login_attempts", "last_invalid_login", "removed_tag_expiration_s", "enabled", "invoice_email_address", "company", "family_name", "given_name", "location", "maximum_queued_builds_count", "creation_date", "last_accessed") VALUES (5, '00000000-0000-0000-0000-000000000005', 'existing-email-org', NULL, 'existing@example.com', 1, NULL, 1, 0, 0, 0, '2026-01-01 00:00:00 +0000 UTC', 1209600, 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);

INSERT INTO "organizationcontactemail" ("id", "organization_id", "contact_email") VALUES (1, 1, 'restored@example.com');
INSERT INTO "organizationcontactemail" ("id", "organization_id", "contact_email") VALUES (2, 4, 'copied-placeholder-without-at-sign');
INSERT INTO "organizationcontactemail" ("id", "organization_id", "contact_email") VALUES (3, 5, 'replacement@example.com');
INSERT INTO "organizationcontactemail" ("id", "organization_id", "contact_email") VALUES (4, 3, 'organization-contact-address-that-is-definitely-longer-than-sixty-four-characters@example.com');

INSERT INTO "logentrykind" ("id", "name") VALUES (140, 'tag_made_immutable_by_policy');
INSERT INTO "logentrykind" ("id", "name") VALUES (141, 'tags_made_immutable_by_policy');
INSERT INTO "logentrykind" ("id", "name") VALUES (142, 'change_tag_immutability');
INSERT INTO "logentrykind" ("id", "name") VALUES (143, 'create_robot_federation');
INSERT INTO "logentrykind" ("id", "name") VALUES (144, 'delete_robot_federation');
INSERT INTO "logentrykind" ("id", "name") VALUES (145, 'federated_robot_token_exchange');
INSERT INTO "logentrykind" ("id", "name") VALUES (146, 'export_logs_success');
INSERT INTO "logentrykind" ("id", "name") VALUES (147, 'export_logs_failure');
INSERT INTO "logentrykind" ("id", "name") VALUES (148, 'org_create_quota');
INSERT INTO "logentrykind" ("id", "name") VALUES (149, 'org_change_quota');
INSERT INTO "logentrykind" ("id", "name") VALUES (150, 'org_delete_quota');
INSERT INTO "logentrykind" ("id", "name") VALUES (151, 'org_create_quota_limit');
INSERT INTO "logentrykind" ("id", "name") VALUES (152, 'org_change_quota_limit');
INSERT INTO "logentrykind" ("id", "name") VALUES (153, 'org_delete_quota_limit');
INSERT INTO "logentrykind" ("id", "name") VALUES (154, 'org_mirror_enabled');
INSERT INTO "logentrykind" ("id", "name") VALUES (155, 'org_mirror_disabled');
INSERT INTO "logentrykind" ("id", "name") VALUES (156, 'org_mirror_config_changed');
INSERT INTO "logentrykind" ("id", "name") VALUES (157, 'org_mirror_sync_started');
INSERT INTO "logentrykind" ("id", "name") VALUES (158, 'org_mirror_sync_completed');
INSERT INTO "logentrykind" ("id", "name") VALUES (159, 'org_mirror_sync_failed');
INSERT INTO "logentrykind" ("id", "name") VALUES (160, 'org_mirror_sync_tag_started');
INSERT INTO "logentrykind" ("id", "name") VALUES (161, 'org_mirror_sync_tag_completed');
INSERT INTO "logentrykind" ("id", "name") VALUES (162, 'org_mirror_repo_created');
INSERT INTO "logentrykind" ("id", "name") VALUES (163, 'create_immutability_policy');
INSERT INTO "logentrykind" ("id", "name") VALUES (164, 'update_immutability_policy');
INSERT INTO "logentrykind" ("id", "name") VALUES (165, 'delete_immutability_policy');
INSERT INTO "logentrykind" ("id", "name") VALUES (166, 'org_mirror_repo_creation_failed');
INSERT INTO "logentrykind" ("id", "name") VALUES (167, 'create_namespace_notification');
INSERT INTO "logentrykind" ("id", "name") VALUES (168, 'delete_namespace_notification');
INSERT INTO "logentrykind" ("id", "name") VALUES (169, 'reset_namespace_notification');

INSERT INTO "externalnotificationevent" ("id", "name") VALUES (1, 'quota_warning');
INSERT INTO "externalnotificationevent" ("id", "name") VALUES (2, 'quota_error');
