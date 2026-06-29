-- revision: c3d4e5f6a7b8
-- Bridge migration: brings any OMR v2.0.x SQLite database to the
-- Go binary's target schema. All statements are idempotent.

-- ============================================================
-- SECTION 1: New tables
-- ============================================================

CREATE TABLE IF NOT EXISTS tagpullstatistics (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	tag_name VARCHAR(255) NOT NULL,
	tag_pull_count BIGINT NOT NULL,
	last_tag_pull_date DATETIME NOT NULL,
	current_manifest_digest VARCHAR(255),
	CONSTRAINT pk_tagpullstatistics PRIMARY KEY (id),
	CONSTRAINT fk_tagpullstatistics_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE IF NOT EXISTS manifestpullstatistics (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_digest VARCHAR(255) NOT NULL,
	manifest_pull_count BIGINT NOT NULL,
	last_manifest_pull_date DATETIME NOT NULL,
	CONSTRAINT pk_manifestpullstatistics PRIMARY KEY (id),
	CONSTRAINT fk_manifestpullstatistics_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE IF NOT EXISTS orgmirrorconfig (
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

CREATE TABLE IF NOT EXISTS orgmirrorrepository (
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

CREATE TABLE IF NOT EXISTS namespaceimmutabilitypolicy (
	id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	CONSTRAINT pk_namespaceimmutabilitypolicyid PRIMARY KEY (id),
	CONSTRAINT fk_namespaceimmutabilitypolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS repositoryimmutabilitypolicy (
	id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	repository_id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	CONSTRAINT pk_repositoryimmutabilitypolicyid PRIMARY KEY (id),
	CONSTRAINT fk_repositoryimmutabilitypolicy_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repositoryimmutabilitypolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS organizationcontactemail (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	contact_email VARCHAR(255),
	CONSTRAINT pk_organizationcontactemail PRIMARY KEY (id),
	CONSTRAINT fk_organizationcontactemail_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id)
);

-- ============================================================
-- SECTION 2: Indexes on new tables
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS tagpullstatistics_repository_id_tag_name ON tagpullstatistics (repository_id, tag_name);
CREATE UNIQUE INDEX IF NOT EXISTS manifestpullstatistics_repository_id_manifest_digest ON manifestpullstatistics (repository_id, manifest_digest);
CREATE UNIQUE INDEX IF NOT EXISTS orgmirrorconfig_organization_id ON orgmirrorconfig (organization_id);
CREATE INDEX IF NOT EXISTS orgmirrorconfig_internal_robot_id ON orgmirrorconfig (internal_robot_id);
CREATE INDEX IF NOT EXISTS orgmirrorconfig_sync_status ON orgmirrorconfig (sync_status);
CREATE INDEX IF NOT EXISTS orgmirrorconfig_sync_start_date ON orgmirrorconfig (sync_start_date);
CREATE INDEX IF NOT EXISTS orgmirrorrepository_org_mirror_config_id ON orgmirrorrepository (org_mirror_config_id);
CREATE INDEX IF NOT EXISTS orgmirrorrepository_repository_id ON orgmirrorrepository (repository_id);
CREATE INDEX IF NOT EXISTS orgmirrorrepository_sync_status ON orgmirrorrepository (sync_status);
CREATE UNIQUE INDEX IF NOT EXISTS orgmirrorrepository_config_repo_name ON orgmirrorrepository (org_mirror_config_id, repository_name);
CREATE INDEX IF NOT EXISTS orgmirrorrepository_config_status ON orgmirrorrepository (org_mirror_config_id, sync_status);
CREATE INDEX IF NOT EXISTS namespaceimmutabilitypolicy_namespace_id ON namespaceimmutabilitypolicy (namespace_id);
CREATE UNIQUE INDEX IF NOT EXISTS namespaceimmutabilitypolicy_uuid ON namespaceimmutabilitypolicy (uuid);
CREATE INDEX IF NOT EXISTS repositoryimmutabilitypolicy_repository_id ON repositoryimmutabilitypolicy (repository_id);
CREATE INDEX IF NOT EXISTS repositoryimmutabilitypolicy_namespace_id ON repositoryimmutabilitypolicy (namespace_id);
CREATE UNIQUE INDEX IF NOT EXISTS repositoryimmutabilitypolicy_uuid ON repositoryimmutabilitypolicy (uuid);
CREATE UNIQUE INDEX IF NOT EXISTS organizationcontactemail_organization_id ON organizationcontactemail (organization_id);
CREATE INDEX IF NOT EXISTS organizationcontactemail_contact_email ON organizationcontactemail (contact_email);

-- ============================================================
-- SECTION 3: Indexes on existing tables
-- ============================================================

CREATE INDEX IF NOT EXISTS tag_repository_id_immutable ON tag (repository_id, immutable);
CREATE INDEX IF NOT EXISTS tag_manifest_id_immutable ON tag (manifest_id, immutable);
CREATE INDEX IF NOT EXISTS tag_manifest_id_lifetime_end_ms ON tag (manifest_id, lifetime_end_ms);
CREATE INDEX IF NOT EXISTS manifest_repository_id_artifact_type ON manifest (repository_id, artifact_type);
CREATE INDEX IF NOT EXISTS manifest_artifact_type_backfilled ON manifest (artifact_type_backfilled);

-- ============================================================
-- SECTION 4: Dropped tables
-- ============================================================

DROP TABLE IF EXISTS namespacegeorestriction;

-- ============================================================
-- SECTION 5: Seed data (logentrykind)
-- ============================================================

INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_tag_immutability');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_robot_federation');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_robot_federation');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('federated_robot_token_exchange');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('export_logs_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('export_logs_failure');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_create_quota');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_quota');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete_quota');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_create_quota_limit');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_quota_limit');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete_quota_limit');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_enabled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_disabled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_config_changed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_started');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_completed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_tag_started');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_tag_completed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_repo_created');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_immutability_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('update_immutability_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_immutability_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_repo_creation_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('tag_made_immutable_by_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('tags_made_immutable_by_policy');

-- ============================================================
-- SECTION 6: Data migration
-- ============================================================

INSERT OR IGNORE INTO organizationcontactemail (organization_id, contact_email)
SELECT id, email FROM "user" WHERE organization = 1 AND email IS NOT NULL;
