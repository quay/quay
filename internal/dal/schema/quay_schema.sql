-- Auto-generated from Peewee models via tools/export_schema_ddl.py
-- DO NOT EDIT - run 'make go-schema' to regenerate

CREATE TABLE accesstokenkind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_accesstokenkind PRIMARY KEY (id)
);

CREATE TABLE buildtriggerservice (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_buildtriggerservice PRIMARY KEY (id)
);

CREATE TABLE disablereason (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_disablereason PRIMARY KEY (id)
);

CREATE TABLE externalnotificationevent (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_externalnotificationevent PRIMARY KEY (id)
);

CREATE TABLE externalnotificationmethod (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_externalnotificationmethod PRIMARY KEY (id)
);

CREATE TABLE imagestorage (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	image_size BIGINT, 
	uncompressed_size BIGINT, 
	uploading BOOLEAN, 
	cas_path BOOLEAN NOT NULL, 
	content_checksum VARCHAR(255), 
	CONSTRAINT pk_imagestorage PRIMARY KEY (id)
);

CREATE TABLE imagestoragelocation (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_imagestoragelocation PRIMARY KEY (id)
);

CREATE TABLE imagestoragesignaturekind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_imagestoragesignaturekind PRIMARY KEY (id)
);

CREATE TABLE imagestoragetransformation (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_imagestoragetransformation PRIMARY KEY (id)
);

CREATE TABLE labelsourcetype (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	mutable BOOLEAN NOT NULL, 
	CONSTRAINT pk_labelsourcetype PRIMARY KEY (id)
);

CREATE TABLE logentry3 (
	id INTEGER NOT NULL, 
	kind_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	performer_id INTEGER, 
	repository_id INTEGER, 
	datetime DATETIME NOT NULL, 
	ip VARCHAR(255), 
	metadata_json TEXT NOT NULL, 
	CONSTRAINT pk_logentry3 PRIMARY KEY (id)
);

CREATE TABLE logentrykind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_logentrykind PRIMARY KEY (id)
);

CREATE TABLE loginservice (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_loginservice PRIMARY KEY (id)
);

CREATE TABLE mediatype (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_mediatype PRIMARY KEY (id)
);

CREATE TABLE notificationkind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_notificationkind PRIMARY KEY (id)
);

CREATE TABLE quayregion (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_quayregion PRIMARY KEY (id)
);

CREATE TABLE quayservice (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_quayservice PRIMARY KEY (id)
);

CREATE TABLE queueitem (
	id INTEGER NOT NULL, 
	queue_name VARCHAR(1024) NOT NULL, 
	body TEXT NOT NULL, 
	available_after DATETIME NOT NULL, 
	available BOOLEAN NOT NULL, 
	processing_expires DATETIME, 
	retries_remaining INTEGER NOT NULL, 
	state_id VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_queueitem PRIMARY KEY (id)
);

CREATE TABLE quotaregistrysize (
	id INTEGER NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	running BOOLEAN NOT NULL, 
	queued BOOLEAN NOT NULL, 
	completed_ms BIGINT, 
	CONSTRAINT pk_quotaregistrysize PRIMARY KEY (id)
);

CREATE TABLE quotatype (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_quotatype PRIMARY KEY (id)
);

CREATE TABLE repositorykind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_repositorykind PRIMARY KEY (id)
);

CREATE TABLE role (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_role PRIMARY KEY (id)
);

CREATE TABLE tagkind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_tagkind PRIMARY KEY (id)
);

CREATE TABLE teamrole (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_teamrole PRIMARY KEY (id)
);

CREATE TABLE user (
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
	invalid_login_attempts INTEGER NOT NULL, 
	last_invalid_login DATETIME NOT NULL, 
	removed_tag_expiration_s BIGINT NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	invoice_email_address VARCHAR(255), 
	given_name VARCHAR(255), 
	family_name VARCHAR(255), 
	company VARCHAR(255), 
	location VARCHAR(255), 
	maximum_queued_builds_count INTEGER, 
	creation_date DATETIME, 
	last_accessed DATETIME, 
	CONSTRAINT pk_user PRIMARY KEY (id)
);

CREATE TABLE userpromptkind (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_userpromptkind PRIMARY KEY (id)
);

CREATE TABLE visibility (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_visibility PRIMARY KEY (id)
);

CREATE TABLE appspecificauthtoken (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	token_name VARCHAR(255) NOT NULL, 
	token_secret VARCHAR(255) NOT NULL, 
	created DATETIME NOT NULL, 
	expiration DATETIME, 
	last_accessed DATETIME, 
	CONSTRAINT pk_appspecificauthtoken PRIMARY KEY (id), 
	CONSTRAINT fk_appspecificauthtoken_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);

CREATE TABLE autoprunetaskstatus (
	id INTEGER NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	last_ran_ms BIGINT, 
	status TEXT, 
	CONSTRAINT pk_autoprunetaskstatus PRIMARY KEY (id), 
	CONSTRAINT fk_autoprunetaskstatus_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE deletednamespace (
	id INTEGER NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	marked DATETIME NOT NULL, 
	original_username VARCHAR(255) NOT NULL, 
	original_email VARCHAR(255) NOT NULL, 
	queue_id VARCHAR(255), 
	CONSTRAINT pk_deletednamespace PRIMARY KEY (id), 
	CONSTRAINT fk_deletednamespace_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE emailconfirmation (
	id INTEGER NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	verification_code VARCHAR(255), 
	user_id INTEGER NOT NULL, 
	pw_reset BOOLEAN NOT NULL, 
	new_email VARCHAR(255), 
	email_confirm BOOLEAN NOT NULL, 
	created DATETIME NOT NULL, 
	CONSTRAINT pk_emailconfirmation PRIMARY KEY (id), 
	CONSTRAINT fk_emailconfirmation_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);

CREATE TABLE federatedlogin (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	service_id INTEGER NOT NULL, 
	service_ident VARCHAR(255) NOT NULL, 
	metadata_json TEXT NOT NULL, 
	CONSTRAINT pk_federatedlogin PRIMARY KEY (id), 
	CONSTRAINT fk_federatedlogin_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_federatedlogin_service_id_loginservice FOREIGN KEY(service_id) REFERENCES loginservice (id)
);

CREATE TABLE imagestorageplacement (
	id INTEGER NOT NULL, 
	storage_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	CONSTRAINT pk_imagestorageplacement PRIMARY KEY (id), 
	CONSTRAINT fk_imagestorageplacement_storage_id_imagestorage FOREIGN KEY(storage_id) REFERENCES imagestorage (id), 
	CONSTRAINT fk_imagestorageplacement_location_id_imagestoragelocation FOREIGN KEY(location_id) REFERENCES imagestoragelocation (id)
);

CREATE TABLE imagestoragesignature (
	id INTEGER NOT NULL, 
	storage_id INTEGER NOT NULL, 
	kind_id INTEGER NOT NULL, 
	signature TEXT, 
	uploading BOOLEAN, 
	CONSTRAINT pk_imagestoragesignature PRIMARY KEY (id), 
	CONSTRAINT fk_imagestoragesignature_storage_id_imagestorage FOREIGN KEY(storage_id) REFERENCES imagestorage (id), 
	CONSTRAINT fk_imagestoragesignature_kind_id_imagestoragesignaturekind FOREIGN KEY(kind_id) REFERENCES imagestoragesignaturekind (id)
);

CREATE TABLE label (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	"key" VARCHAR(255) NOT NULL, 
	value TEXT NOT NULL, 
	media_type_id INTEGER NOT NULL, 
	source_type_id INTEGER NOT NULL, 
	CONSTRAINT pk_label PRIMARY KEY (id), 
	CONSTRAINT fk_label_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id), 
	CONSTRAINT fk_label_source_type_id_labelsourcetype FOREIGN KEY(source_type_id) REFERENCES labelsourcetype (id)
);

CREATE TABLE logentry (
	id INTEGER NOT NULL, 
	kind_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	performer_id INTEGER, 
	repository_id INTEGER, 
	datetime DATETIME NOT NULL, 
	ip VARCHAR(255), 
	metadata_json TEXT NOT NULL, 
	CONSTRAINT pk_logentry PRIMARY KEY (id), 
	CONSTRAINT fk_logentry_kind_id_logentrykind FOREIGN KEY(kind_id) REFERENCES logentrykind (id)
);

CREATE TABLE logentry2 (
	id INTEGER NOT NULL, 
	kind_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	performer_id INTEGER, 
	repository_id INTEGER, 
	datetime DATETIME NOT NULL, 
	ip VARCHAR(255), 
	metadata_json TEXT NOT NULL, 
	CONSTRAINT pk_logentry2 PRIMARY KEY (id), 
	CONSTRAINT fk_logentry2_kind_id_logentrykind FOREIGN KEY(kind_id) REFERENCES logentrykind (id)
);

CREATE TABLE messages (
	id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	severity VARCHAR(255) NOT NULL, 
	media_type_id INTEGER NOT NULL, 
	CONSTRAINT pk_messages PRIMARY KEY (id), 
	CONSTRAINT fk_messages_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);

CREATE TABLE namespaceautoprunepolicy (
	id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	policy TEXT NOT NULL, 
	CONSTRAINT pk_namespaceautoprunepolicy PRIMARY KEY (id), 
	CONSTRAINT fk_namespaceautoprunepolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE namespaceimmutabilitypolicy (
	id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	policy TEXT NOT NULL, 
	CONSTRAINT pk_namespaceimmutabilitypolicy PRIMARY KEY (id), 
	CONSTRAINT fk_namespaceimmutabilitypolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE notification (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	kind_id INTEGER NOT NULL, 
	target_id INTEGER NOT NULL, 
	metadata_json TEXT NOT NULL, 
	created DATETIME NOT NULL, 
	dismissed BOOLEAN NOT NULL, 
	lookup_path VARCHAR(255), 
	CONSTRAINT pk_notification PRIMARY KEY (id), 
	CONSTRAINT fk_notification_kind_id_notificationkind FOREIGN KEY(kind_id) REFERENCES notificationkind (id), 
	CONSTRAINT fk_notification_target_id_user FOREIGN KEY(target_id) REFERENCES user (id)
);

CREATE TABLE oauthapplication (
	id INTEGER NOT NULL, 
	client_id VARCHAR(255) NOT NULL, 
	secure_client_secret VARCHAR(255), 
	fully_migrated BOOLEAN NOT NULL, 
	redirect_uri VARCHAR(255) NOT NULL, 
	application_uri VARCHAR(255) NOT NULL, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	gravatar_email VARCHAR(255), 
	CONSTRAINT pk_oauthapplication PRIMARY KEY (id), 
	CONSTRAINT fk_oauthapplication_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id)
);

CREATE TABLE organizationcontactemail (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	contact_email VARCHAR(255), 
	CONSTRAINT pk_organizationcontactemail PRIMARY KEY (id), 
	CONSTRAINT fk_organizationcontactemail_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id)
);

CREATE TABLE organizationrhskus (
	id INTEGER NOT NULL, 
	subscription_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	org_id INTEGER NOT NULL, 
	quantity INTEGER, 
	CONSTRAINT pk_organizationrhskus PRIMARY KEY (id), 
	CONSTRAINT fk_organizationrhskus_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_organizationrhskus_org_id_user FOREIGN KEY(org_id) REFERENCES user (id)
);

CREATE TABLE orgmirrorconfig (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	creation_date DATETIME NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	mirror_type INTEGER NOT NULL, 
	external_registry_type INTEGER NOT NULL, 
	external_registry_url VARCHAR(2048) NOT NULL, 
	external_namespace VARCHAR(255) NOT NULL, 
	external_registry_username VARCHAR(4096), 
	external_registry_password VARCHAR(9000), 
	external_registry_config TEXT NOT NULL, 
	internal_robot_id INTEGER NOT NULL, 
	repository_filters TEXT NOT NULL, 
	architecture_filter TEXT NOT NULL, 
	visibility_id INTEGER NOT NULL, 
	delete_stale_repos BOOLEAN NOT NULL, 
	sync_interval INTEGER NOT NULL, 
	sync_start_date DATETIME, 
	sync_expiration_date DATETIME, 
	sync_retries_remaining INTEGER NOT NULL, 
	sync_status INTEGER NOT NULL, 
	sync_transaction_id VARCHAR(36) NOT NULL, 
	skopeo_timeout BIGINT NOT NULL, 
	CONSTRAINT pk_orgmirrorconfig PRIMARY KEY (id), 
	CONSTRAINT fk_orgmirrorconfig_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id), 
	CONSTRAINT fk_orgmirrorconfig_internal_robot_id_user FOREIGN KEY(internal_robot_id) REFERENCES user (id), 
	CONSTRAINT fk_orgmirrorconfig_visibility_id_visibility FOREIGN KEY(visibility_id) REFERENCES visibility (id)
);

CREATE TABLE proxycacheconfig (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	creation_date DATETIME NOT NULL, 
	upstream_registry VARCHAR(270) NOT NULL, 
	upstream_registry_username VARCHAR(4096), 
	upstream_registry_password VARCHAR(4096), 
	expiration_s INTEGER NOT NULL, 
	insecure BOOLEAN NOT NULL, 
	CONSTRAINT pk_proxycacheconfig PRIMARY KEY (id), 
	CONSTRAINT fk_proxycacheconfig_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id)
);

CREATE TABLE quayrelease (
	id INTEGER NOT NULL, 
	service_id INTEGER NOT NULL, 
	version VARCHAR(255) NOT NULL, 
	region_id INTEGER NOT NULL, 
	reverted BOOLEAN NOT NULL, 
	created DATETIME NOT NULL, 
	CONSTRAINT pk_quayrelease PRIMARY KEY (id), 
	CONSTRAINT fk_quayrelease_service_id_quayservice FOREIGN KEY(service_id) REFERENCES quayservice (id), 
	CONSTRAINT fk_quayrelease_region_id_quayregion FOREIGN KEY(region_id) REFERENCES quayregion (id)
);

CREATE TABLE quotanamespacesize (
	id INTEGER NOT NULL, 
	namespace_user_id INTEGER NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	backfill_start_ms BIGINT, 
	backfill_complete BOOLEAN NOT NULL, 
	CONSTRAINT pk_quotanamespacesize PRIMARY KEY (id), 
	CONSTRAINT fk_quotanamespacesize_namespace_user_id_user FOREIGN KEY(namespace_user_id) REFERENCES user (id)
);

CREATE TABLE redhatsubscriptions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	account_number INTEGER NOT NULL, 
	CONSTRAINT pk_redhatsubscriptions PRIMARY KEY (id), 
	CONSTRAINT fk_redhatsubscriptions_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);

CREATE TABLE repository (
	id INTEGER NOT NULL, 
	namespace_user_id INTEGER, 
	name VARCHAR(255) NOT NULL, 
	visibility_id INTEGER NOT NULL, 
	description TEXT, 
	badge_token VARCHAR(255) NOT NULL, 
	kind_id INTEGER NOT NULL, 
	trust_enabled BOOLEAN NOT NULL, 
	state INTEGER NOT NULL, 
	CONSTRAINT pk_repository PRIMARY KEY (id), 
	CONSTRAINT fk_repository_namespace_user_id_user FOREIGN KEY(namespace_user_id) REFERENCES user (id), 
	CONSTRAINT fk_repository_visibility_id_visibility FOREIGN KEY(visibility_id) REFERENCES visibility (id), 
	CONSTRAINT fk_repository_kind_id_repositorykind FOREIGN KEY(kind_id) REFERENCES repositorykind (id)
);

CREATE TABLE robotaccountmetadata (
	id INTEGER NOT NULL, 
	robot_account_id INTEGER NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	unstructured_json TEXT NOT NULL, 
	CONSTRAINT pk_robotaccountmetadata PRIMARY KEY (id), 
	CONSTRAINT fk_robotaccountmetadata_robot_account_id_user FOREIGN KEY(robot_account_id) REFERENCES user (id)
);

CREATE TABLE robotaccounttoken (
	id INTEGER NOT NULL, 
	robot_account_id INTEGER NOT NULL, 
	token VARCHAR(255) NOT NULL, 
	fully_migrated BOOLEAN NOT NULL, 
	CONSTRAINT pk_robotaccounttoken PRIMARY KEY (id), 
	CONSTRAINT fk_robotaccounttoken_robot_account_id_user FOREIGN KEY(robot_account_id) REFERENCES user (id)
);

CREATE TABLE servicekeyapproval (
	id INTEGER NOT NULL, 
	approver_id INTEGER, 
	approval_type VARCHAR(255) NOT NULL, 
	approved_date DATETIME NOT NULL, 
	notes TEXT NOT NULL, 
	CONSTRAINT pk_servicekeyapproval PRIMARY KEY (id), 
	CONSTRAINT fk_servicekeyapproval_approver_id_user FOREIGN KEY(approver_id) REFERENCES user (id)
);

CREATE TABLE team (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	organization_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	description TEXT NOT NULL, 
	CONSTRAINT pk_team PRIMARY KEY (id), 
	CONSTRAINT fk_team_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id), 
	CONSTRAINT fk_team_role_id_teamrole FOREIGN KEY(role_id) REFERENCES teamrole (id)
);

CREATE TABLE userorganizationquota (
	id INTEGER NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	limit_bytes BIGINT NOT NULL, 
	CONSTRAINT pk_userorganizationquota PRIMARY KEY (id), 
	CONSTRAINT fk_userorganizationquota_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE userprompt (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	kind_id INTEGER NOT NULL, 
	CONSTRAINT pk_userprompt PRIMARY KEY (id), 
	CONSTRAINT fk_userprompt_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_userprompt_kind_id_userpromptkind FOREIGN KEY(kind_id) REFERENCES userpromptkind (id)
);

CREATE TABLE userregion (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	CONSTRAINT pk_userregion PRIMARY KEY (id), 
	CONSTRAINT fk_userregion_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_userregion_location_id_imagestoragelocation FOREIGN KEY(location_id) REFERENCES imagestoragelocation (id)
);

CREATE TABLE accesstoken (
	id INTEGER NOT NULL, 
	friendly_name VARCHAR(255), 
	token_name VARCHAR(255) NOT NULL, 
	token_code VARCHAR(255) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	created DATETIME NOT NULL, 
	role_id INTEGER NOT NULL, 
	"temporary" BOOLEAN NOT NULL, 
	kind_id INTEGER, 
	CONSTRAINT pk_accesstoken PRIMARY KEY (id), 
	CONSTRAINT fk_accesstoken_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_accesstoken_role_id_role FOREIGN KEY(role_id) REFERENCES role (id), 
	CONSTRAINT fk_accesstoken_kind_id_accesstokenkind FOREIGN KEY(kind_id) REFERENCES accesstokenkind (id)
);

CREATE TABLE blobupload (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	byte_count BIGINT NOT NULL, 
	sha_state TEXT, 
	location_id INTEGER NOT NULL, 
	storage_metadata TEXT, 
	chunk_count INTEGER NOT NULL, 
	uncompressed_byte_count BIGINT, 
	created DATETIME NOT NULL, 
	piece_sha_state TEXT, 
	piece_hashes TEXT, 
	CONSTRAINT pk_blobupload PRIMARY KEY (id), 
	CONSTRAINT fk_blobupload_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_blobupload_location_id_imagestoragelocation FOREIGN KEY(location_id) REFERENCES imagestoragelocation (id)
);

CREATE TABLE deletedrepository (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	marked DATETIME NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	queue_id VARCHAR(255), 
	CONSTRAINT pk_deletedrepository PRIMARY KEY (id), 
	CONSTRAINT fk_deletedrepository_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE manifest (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	digest VARCHAR(255) NOT NULL, 
	media_type_id INTEGER NOT NULL, 
	manifest_bytes TEXT NOT NULL, 
	config_media_type VARCHAR(255), 
	layers_compressed_size BIGINT, 
	subject VARCHAR(255), 
	subject_backfilled BOOLEAN NOT NULL, 
	artifact_type VARCHAR(255), 
	artifact_type_backfilled BOOLEAN NOT NULL, 
	CONSTRAINT pk_manifest PRIMARY KEY (id), 
	CONSTRAINT fk_manifest_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_manifest_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
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

CREATE TABLE oauthaccesstoken (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	application_id INTEGER NOT NULL, 
	authorized_user_id INTEGER NOT NULL, 
	scope VARCHAR(255) NOT NULL, 
	token_name VARCHAR(255) NOT NULL, 
	token_code VARCHAR(255) NOT NULL, 
	token_type VARCHAR(255) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	data TEXT NOT NULL, 
	CONSTRAINT pk_oauthaccesstoken PRIMARY KEY (id), 
	CONSTRAINT fk_oauthaccesstoken_application_id_oauthapplication FOREIGN KEY(application_id) REFERENCES oauthapplication (id), 
	CONSTRAINT fk_oauthaccesstoken_authorized_user_id_user FOREIGN KEY(authorized_user_id) REFERENCES user (id)
);

CREATE TABLE oauthassignedtoken (
	id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	assigned_user_id INTEGER NOT NULL, 
	application_id INTEGER NOT NULL, 
	redirect_uri VARCHAR(255), 
	scope VARCHAR(255) NOT NULL, 
	response_type VARCHAR(255), 
	CONSTRAINT pk_oauthassignedtoken PRIMARY KEY (id), 
	CONSTRAINT fk_oauthassignedtoken_assigned_user_id_user FOREIGN KEY(assigned_user_id) REFERENCES user (id), 
	CONSTRAINT fk_oauthassignedtoken_application_id_oauthapplication FOREIGN KEY(application_id) REFERENCES oauthapplication (id)
);

CREATE TABLE oauthauthorizationcode (
	id INTEGER NOT NULL, 
	application_id INTEGER NOT NULL, 
	code_name VARCHAR(255) NOT NULL, 
	code_credential VARCHAR(255) NOT NULL, 
	scope VARCHAR(255) NOT NULL, 
	data TEXT NOT NULL, 
	CONSTRAINT pk_oauthauthorizationcode PRIMARY KEY (id), 
	CONSTRAINT fk_oauthauthorizationcode_application_id_oauthapplication FOREIGN KEY(application_id) REFERENCES oauthapplication (id)
);

CREATE TABLE orgmirrorrepository (
	id INTEGER NOT NULL, 
	org_mirror_config_id INTEGER NOT NULL, 
	repository_name VARCHAR(255) NOT NULL, 
	repository_id INTEGER, 
	discovery_date DATETIME NOT NULL, 
	sync_status INTEGER NOT NULL, 
	sync_start_date DATETIME, 
	sync_expiration_date DATETIME, 
	sync_retries_remaining INTEGER NOT NULL, 
	sync_transaction_id VARCHAR(36) NOT NULL, 
	last_sync_date DATETIME, 
	status_message TEXT, 
	creation_date DATETIME NOT NULL, 
	CONSTRAINT pk_orgmirrorrepository PRIMARY KEY (id), 
	CONSTRAINT fk_orgmirrorrepository_org_mirror_config_id_orgmirrorconfig FOREIGN KEY(org_mirror_config_id) REFERENCES orgmirrorconfig (id), 
	CONSTRAINT fk_orgmirrorrepository_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE permissionprototype (
	id INTEGER NOT NULL, 
	org_id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	activating_user_id INTEGER, 
	delegate_user_id INTEGER, 
	delegate_team_id INTEGER, 
	role_id INTEGER NOT NULL, 
	CONSTRAINT pk_permissionprototype PRIMARY KEY (id), 
	CONSTRAINT fk_permissionprototype_org_id_user FOREIGN KEY(org_id) REFERENCES user (id), 
	CONSTRAINT fk_permissionprototype_activating_user_id_user FOREIGN KEY(activating_user_id) REFERENCES user (id), 
	CONSTRAINT fk_permissionprototype_delegate_user_id_user FOREIGN KEY(delegate_user_id) REFERENCES user (id), 
	CONSTRAINT fk_permissionprototype_delegate_team_id_team FOREIGN KEY(delegate_team_id) REFERENCES team (id), 
	CONSTRAINT fk_permissionprototype_role_id_role FOREIGN KEY(role_id) REFERENCES role (id)
);

CREATE TABLE quotalimits (
	id INTEGER NOT NULL, 
	quota_id INTEGER NOT NULL, 
	quota_type_id INTEGER NOT NULL, 
	percent_of_limit INTEGER NOT NULL, 
	CONSTRAINT pk_quotalimits PRIMARY KEY (id), 
	CONSTRAINT fk_quotalimits_quota_id_userorganizationquota FOREIGN KEY(quota_id) REFERENCES userorganizationquota (id), 
	CONSTRAINT fk_quotalimits_quota_type_id_quotatype FOREIGN KEY(quota_type_id) REFERENCES quotatype (id)
);

CREATE TABLE quotarepositorysize (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	backfill_start_ms BIGINT, 
	backfill_complete BOOLEAN NOT NULL, 
	CONSTRAINT pk_quotarepositorysize PRIMARY KEY (id), 
	CONSTRAINT fk_quotarepositorysize_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE repomirrorrule (
	id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	creation_date DATETIME NOT NULL, 
	rule_type INTEGER NOT NULL, 
	rule_value TEXT NOT NULL, 
	left_child_id INTEGER, 
	right_child_id INTEGER, 
	CONSTRAINT pk_repomirrorrule PRIMARY KEY (id), 
	CONSTRAINT fk_repomirrorrule_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repomirrorrule_left_child_id_repomirrorrule FOREIGN KEY(left_child_id) REFERENCES repomirrorrule (id), 
	CONSTRAINT fk_repomirrorrule_right_child_id_repomirrorrule FOREIGN KEY(right_child_id) REFERENCES repomirrorrule (id)
);

CREATE TABLE repositoryactioncount (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	count INTEGER NOT NULL, 
	date DATE NOT NULL, 
	CONSTRAINT pk_repositoryactioncount PRIMARY KEY (id), 
	CONSTRAINT fk_repositoryactioncount_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE repositoryauthorizedemail (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	code VARCHAR(255) NOT NULL, 
	confirmed BOOLEAN NOT NULL, 
	CONSTRAINT pk_repositoryauthorizedemail PRIMARY KEY (id), 
	CONSTRAINT fk_repositoryauthorizedemail_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE repositoryautoprunepolicy (
	id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	policy TEXT NOT NULL, 
	CONSTRAINT pk_repositoryautoprunepolicy PRIMARY KEY (id), 
	CONSTRAINT fk_repositoryautoprunepolicy_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repositoryautoprunepolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE repositoryimmutabilitypolicy (
	id INTEGER NOT NULL, 
	uuid VARCHAR(36) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	namespace_id INTEGER NOT NULL, 
	policy TEXT NOT NULL, 
	CONSTRAINT pk_repositoryimmutabilitypolicy PRIMARY KEY (id), 
	CONSTRAINT fk_repositoryimmutabilitypolicy_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repositoryimmutabilitypolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);

CREATE TABLE repositorynotification (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	event_id INTEGER NOT NULL, 
	method_id INTEGER NOT NULL, 
	title VARCHAR(255), 
	config_json TEXT NOT NULL, 
	event_config_json TEXT NOT NULL, 
	number_of_failures INTEGER NOT NULL, 
	last_ran_ms BIGINT, 
	CONSTRAINT pk_repositorynotification PRIMARY KEY (id), 
	CONSTRAINT fk_repositorynotification_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repositorynotification_event_id_externalnotificationevent FOREIGN KEY(event_id) REFERENCES externalnotificationevent (id), 
	CONSTRAINT fk_repositorynotification_method_id_externalnotificationmethod FOREIGN KEY(method_id) REFERENCES externalnotificationmethod (id)
);

CREATE TABLE repositorypermission (
	id INTEGER NOT NULL, 
	team_id INTEGER, 
	user_id INTEGER, 
	repository_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	CONSTRAINT pk_repositorypermission PRIMARY KEY (id), 
	CONSTRAINT fk_repositorypermission_team_id_team FOREIGN KEY(team_id) REFERENCES team (id), 
	CONSTRAINT fk_repositorypermission_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_repositorypermission_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repositorypermission_role_id_role FOREIGN KEY(role_id) REFERENCES role (id)
);

CREATE TABLE repositorysearchscore (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	score BIGINT NOT NULL, 
	last_updated DATETIME, 
	CONSTRAINT pk_repositorysearchscore PRIMARY KEY (id), 
	CONSTRAINT fk_repositorysearchscore_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE servicekey (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	kid VARCHAR(255) NOT NULL, 
	service VARCHAR(255) NOT NULL, 
	jwk TEXT NOT NULL, 
	metadata TEXT NOT NULL, 
	created_date DATETIME NOT NULL, 
	expiration_date DATETIME, 
	rotation_duration INTEGER, 
	approval_id INTEGER, 
	CONSTRAINT pk_servicekey PRIMARY KEY (id), 
	CONSTRAINT fk_servicekey_approval_id_servicekeyapproval FOREIGN KEY(approval_id) REFERENCES servicekeyapproval (id)
);

CREATE TABLE star (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	created DATETIME NOT NULL, 
	CONSTRAINT pk_star PRIMARY KEY (id), 
	CONSTRAINT fk_star_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_star_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

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

CREATE TABLE teammember (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	team_id INTEGER NOT NULL, 
	CONSTRAINT pk_teammember PRIMARY KEY (id), 
	CONSTRAINT fk_teammember_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_teammember_team_id_team FOREIGN KEY(team_id) REFERENCES team (id)
);

CREATE TABLE teammemberinvite (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	email VARCHAR(255), 
	team_id INTEGER NOT NULL, 
	inviter_id INTEGER NOT NULL, 
	invite_token VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_teammemberinvite PRIMARY KEY (id), 
	CONSTRAINT fk_teammemberinvite_user_id_user FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT fk_teammemberinvite_team_id_team FOREIGN KEY(team_id) REFERENCES team (id), 
	CONSTRAINT fk_teammemberinvite_inviter_id_user FOREIGN KEY(inviter_id) REFERENCES user (id)
);

CREATE TABLE teamsync (
	id INTEGER NOT NULL, 
	team_id INTEGER NOT NULL, 
	transaction_id VARCHAR(255) NOT NULL, 
	last_updated DATETIME, 
	service_id INTEGER NOT NULL, 
	config TEXT NOT NULL, 
	CONSTRAINT pk_teamsync PRIMARY KEY (id), 
	CONSTRAINT fk_teamsync_team_id_team FOREIGN KEY(team_id) REFERENCES team (id), 
	CONSTRAINT fk_teamsync_service_id_loginservice FOREIGN KEY(service_id) REFERENCES loginservice (id)
);

CREATE TABLE uploadedblob (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	blob_id INTEGER NOT NULL, 
	uploaded_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	CONSTRAINT pk_uploadedblob PRIMARY KEY (id), 
	CONSTRAINT fk_uploadedblob_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_uploadedblob_blob_id_imagestorage FOREIGN KEY(blob_id) REFERENCES imagestorage (id)
);

CREATE TABLE manifestblob (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	manifest_id INTEGER NOT NULL, 
	blob_id INTEGER NOT NULL, 
	CONSTRAINT pk_manifestblob PRIMARY KEY (id), 
	CONSTRAINT fk_manifestblob_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_manifestblob_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id), 
	CONSTRAINT fk_manifestblob_blob_id_imagestorage FOREIGN KEY(blob_id) REFERENCES imagestorage (id)
);

CREATE TABLE manifestchild (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	manifest_id INTEGER NOT NULL, 
	child_manifest_id INTEGER NOT NULL, 
	CONSTRAINT pk_manifestchild PRIMARY KEY (id), 
	CONSTRAINT fk_manifestchild_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_manifestchild_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id), 
	CONSTRAINT fk_manifestchild_child_manifest_id_manifest FOREIGN KEY(child_manifest_id) REFERENCES manifest (id)
);

CREATE TABLE manifestlabel (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	manifest_id INTEGER NOT NULL, 
	label_id INTEGER NOT NULL, 
	CONSTRAINT pk_manifestlabel PRIMARY KEY (id), 
	CONSTRAINT fk_manifestlabel_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_manifestlabel_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id), 
	CONSTRAINT fk_manifestlabel_label_id_label FOREIGN KEY(label_id) REFERENCES label (id)
);

CREATE TABLE manifestsecuritystatus (
	id INTEGER NOT NULL, 
	manifest_id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	index_status INTEGER NOT NULL, 
	error_json TEXT NOT NULL, 
	last_indexed DATETIME NOT NULL, 
	indexer_hash VARCHAR(128) NOT NULL, 
	indexer_version INTEGER NOT NULL, 
	metadata_json TEXT NOT NULL, 
	CONSTRAINT pk_manifestsecuritystatus PRIMARY KEY (id), 
	CONSTRAINT fk_manifestsecuritystatus_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id), 
	CONSTRAINT fk_manifestsecuritystatus_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);

CREATE TABLE repomirrorconfig (
	id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	creation_date DATETIME NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	mirror_type INTEGER NOT NULL, 
	internal_robot_id INTEGER NOT NULL, 
	external_reference VARCHAR(255) NOT NULL, 
	external_registry_username VARCHAR(4096), 
	external_registry_password VARCHAR(9000), 
	external_registry_config TEXT NOT NULL, 
	architecture_filter TEXT, 
	sync_interval INTEGER NOT NULL, 
	sync_start_date DATETIME, 
	sync_expiration_date DATETIME, 
	sync_retries_remaining INTEGER NOT NULL, 
	sync_status INTEGER NOT NULL, 
	sync_transaction_id VARCHAR(36) NOT NULL, 
	root_rule_id INTEGER NOT NULL, 
	skopeo_timeout BIGINT NOT NULL, 
	CONSTRAINT pk_repomirrorconfig PRIMARY KEY (id), 
	CONSTRAINT fk_repomirrorconfig_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repomirrorconfig_internal_robot_id_user FOREIGN KEY(internal_robot_id) REFERENCES user (id), 
	CONSTRAINT fk_repomirrorconfig_root_rule_id_repomirrorrule FOREIGN KEY(root_rule_id) REFERENCES repomirrorrule (id)
);

CREATE TABLE repositorybuildtrigger (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	service_id INTEGER NOT NULL, 
	repository_id INTEGER NOT NULL, 
	connected_user_id INTEGER NOT NULL, 
	secure_auth_token VARCHAR(255), 
	secure_private_key TEXT, 
	fully_migrated BOOLEAN NOT NULL, 
	config TEXT NOT NULL, 
	write_token_id INTEGER, 
	pull_robot_id INTEGER, 
	enabled BOOLEAN NOT NULL, 
	disabled_reason_id INTEGER, 
	disabled_datetime DATETIME, 
	successive_failure_count INTEGER NOT NULL, 
	successive_internal_error_count INTEGER NOT NULL, 
	CONSTRAINT pk_repositorybuildtrigger PRIMARY KEY (id), 
	CONSTRAINT fk_repositorybuildtrigger_service_id_buildtriggerservice FOREIGN KEY(service_id) REFERENCES buildtriggerservice (id), 
	CONSTRAINT fk_repositorybuildtrigger_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repositorybuildtrigger_connected_user_id_user FOREIGN KEY(connected_user_id) REFERENCES user (id), 
	CONSTRAINT fk_repositorybuildtrigger_write_token_id_accesstoken FOREIGN KEY(write_token_id) REFERENCES accesstoken (id), 
	CONSTRAINT fk_repositorybuildtrigger_pull_robot_id_user FOREIGN KEY(pull_robot_id) REFERENCES user (id), 
	CONSTRAINT fk_repositorybuildtrigger_disabled_reason_id_disablereason FOREIGN KEY(disabled_reason_id) REFERENCES disablereason (id)
);

CREATE TABLE tag (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	manifest_id INTEGER, 
	lifetime_start_ms BIGINT NOT NULL, 
	lifetime_end_ms BIGINT, 
	immutable BOOLEAN NOT NULL, 
	hidden BOOLEAN NOT NULL, 
	reversion BOOLEAN NOT NULL, 
	tag_kind_id INTEGER NOT NULL, 
	linked_tag_id INTEGER, 
	CONSTRAINT pk_tag PRIMARY KEY (id), 
	CONSTRAINT fk_tag_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_tag_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id), 
	CONSTRAINT fk_tag_tag_kind_id_tagkind FOREIGN KEY(tag_kind_id) REFERENCES tagkind (id), 
	CONSTRAINT fk_tag_linked_tag_id_tag FOREIGN KEY(linked_tag_id) REFERENCES tag (id)
);

CREATE TABLE repositorybuild (
	id INTEGER NOT NULL, 
	uuid VARCHAR(255) NOT NULL, 
	repository_id INTEGER NOT NULL, 
	access_token_id INTEGER NOT NULL, 
	resource_key VARCHAR(255), 
	job_config TEXT NOT NULL, 
	phase VARCHAR(255) NOT NULL, 
	started DATETIME NOT NULL, 
	display_name VARCHAR(255) NOT NULL, 
	trigger_id INTEGER, 
	pull_robot_id INTEGER, 
	logs_archived BOOLEAN NOT NULL, 
	queue_id VARCHAR(255), 
	CONSTRAINT pk_repositorybuild PRIMARY KEY (id), 
	CONSTRAINT fk_repositorybuild_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id), 
	CONSTRAINT fk_repositorybuild_access_token_id_accesstoken FOREIGN KEY(access_token_id) REFERENCES accesstoken (id), 
	CONSTRAINT fk_repositorybuild_trigger_id_repositorybuildtrigger FOREIGN KEY(trigger_id) REFERENCES repositorybuildtrigger (id), 
	CONSTRAINT fk_repositorybuild_pull_robot_id_user FOREIGN KEY(pull_robot_id) REFERENCES user (id)
);

CREATE TABLE tagnotificationsuccess (
	id INTEGER NOT NULL, 
	notification_id INTEGER NOT NULL, 
	tag_id INTEGER NOT NULL, 
	method_id INTEGER NOT NULL, 
	CONSTRAINT pk_tagnotificationsuccess PRIMARY KEY (id), 
	CONSTRAINT fk_tagnotificationsuccess_notification_id_repositorynotification FOREIGN KEY(notification_id) REFERENCES repositorynotification (id), 
	CONSTRAINT fk_tagnotificationsuccess_tag_id_tag FOREIGN KEY(tag_id) REFERENCES tag (id), 
	CONSTRAINT fk_tagnotificationsuccess_method_id_externalnotificationmethod FOREIGN KEY(method_id) REFERENCES externalnotificationmethod (id)
);

CREATE UNIQUE INDEX accesstokenkind_name ON accesstokenkind (name);
CREATE UNIQUE INDEX buildtriggerservice_name ON buildtriggerservice (name);
CREATE UNIQUE INDEX disablereason_name ON disablereason (name);
CREATE UNIQUE INDEX externalnotificationevent_name ON externalnotificationevent (name);
CREATE UNIQUE INDEX externalnotificationmethod_name ON externalnotificationmethod (name);
CREATE INDEX imagestorage_content_checksum ON imagestorage (content_checksum);
CREATE UNIQUE INDEX imagestorage_uuid ON imagestorage (uuid);
CREATE UNIQUE INDEX imagestoragelocation_name ON imagestoragelocation (name);
CREATE UNIQUE INDEX imagestoragesignaturekind_name ON imagestoragesignaturekind (name);
CREATE UNIQUE INDEX imagestoragetransformation_name ON imagestoragetransformation (name);
CREATE UNIQUE INDEX labelsourcetype_name ON labelsourcetype (name);
CREATE INDEX logentry3_account_id_datetime ON logentry3 (account_id, datetime);
CREATE INDEX logentry3_datetime ON logentry3 (datetime);
CREATE INDEX logentry3_performer_id_datetime ON logentry3 (performer_id, datetime);
CREATE INDEX logentry3_repository_id_datetime_kind_id ON logentry3 (repository_id, datetime, kind_id);
CREATE UNIQUE INDEX logentrykind_name ON logentrykind (name);
CREATE UNIQUE INDEX loginservice_name ON loginservice (name);
CREATE UNIQUE INDEX mediatype_name ON mediatype (name);
CREATE UNIQUE INDEX notificationkind_name ON notificationkind (name);
CREATE UNIQUE INDEX quayregion_name ON quayregion (name);
CREATE UNIQUE INDEX quayservice_name ON quayservice (name);
CREATE INDEX queueitem_pe_aafter_qname_rremaining_available ON queueitem (processing_expires, available_after, queue_name, retries_remaining, available);
CREATE INDEX queueitem_pexpires_aafter_rremaining_available ON queueitem (processing_expires, available_after, retries_remaining, available);
CREATE INDEX queueitem_processing_expires_available ON queueitem (processing_expires, available);
CREATE INDEX queueitem_processing_expires_queue_name_available ON queueitem (processing_expires, queue_name, available);
CREATE INDEX queueitem_queue_name ON queueitem (queue_name);
CREATE UNIQUE INDEX queueitem_state_id ON queueitem (state_id);
CREATE UNIQUE INDEX repositorykind_name ON repositorykind (name);
CREATE UNIQUE INDEX role_name ON role (name);
CREATE UNIQUE INDEX tagkind_name ON tagkind (name);
CREATE INDEX teamrole_name ON teamrole (name);
CREATE UNIQUE INDEX user_email ON user (email);
CREATE INDEX user_invoice_email_address ON user (invoice_email_address);
CREATE INDEX user_last_accessed ON user (last_accessed);
CREATE INDEX user_organization ON user (organization);
CREATE INDEX user_robot ON user (robot);
CREATE INDEX user_stripe_id ON user (stripe_id);
CREATE UNIQUE INDEX user_username ON user (username);
CREATE INDEX user_uuid ON user (uuid);
CREATE INDEX userpromptkind_name ON userpromptkind (name);
CREATE UNIQUE INDEX visibility_name ON visibility (name);
CREATE UNIQUE INDEX appspecificauthtoken_token_name ON appspecificauthtoken (token_name);
CREATE INDEX appspecificauthtoken_user_id ON appspecificauthtoken (user_id);
CREATE INDEX appspecificauthtoken_user_id_expiration ON appspecificauthtoken (user_id, expiration);
CREATE INDEX appspecificauthtoken_uuid ON appspecificauthtoken (uuid);
CREATE INDEX autoprunetaskstatus_last_ran_ms ON autoprunetaskstatus (last_ran_ms);
CREATE INDEX autoprunetaskstatus_namespace_id ON autoprunetaskstatus (namespace_id);
CREATE UNIQUE INDEX deletednamespace_namespace_id ON deletednamespace (namespace_id);
CREATE INDEX deletednamespace_original_email ON deletednamespace (original_email);
CREATE INDEX deletednamespace_original_username ON deletednamespace (original_username);
CREATE INDEX deletednamespace_queue_id ON deletednamespace (queue_id);
CREATE UNIQUE INDEX emailconfirmation_code ON emailconfirmation (code);
CREATE INDEX emailconfirmation_user_id ON emailconfirmation (user_id);
CREATE INDEX federatedlogin_service_id ON federatedlogin (service_id);
CREATE UNIQUE INDEX federatedlogin_service_id_service_ident ON federatedlogin (service_id, service_ident);
CREATE UNIQUE INDEX federatedlogin_service_id_user_id ON federatedlogin (service_id, user_id);
CREATE INDEX federatedlogin_user_id ON federatedlogin (user_id);
CREATE INDEX imagestorageplacement_location_id ON imagestorageplacement (location_id);
CREATE INDEX imagestorageplacement_storage_id ON imagestorageplacement (storage_id);
CREATE UNIQUE INDEX imagestorageplacement_storage_id_location_id ON imagestorageplacement (storage_id, location_id);
CREATE INDEX imagestoragesignature_kind_id ON imagestoragesignature (kind_id);
CREATE UNIQUE INDEX imagestoragesignature_kind_id_storage_id ON imagestoragesignature (kind_id, storage_id);
CREATE INDEX imagestoragesignature_storage_id ON imagestoragesignature (storage_id);
CREATE INDEX label_key ON label ("key");
CREATE INDEX label_media_type_id ON label (media_type_id);
CREATE INDEX label_source_type_id ON label (source_type_id);
CREATE UNIQUE INDEX label_uuid ON label (uuid);
CREATE INDEX logentry_account_id ON logentry (account_id);
CREATE INDEX logentry_account_id_datetime ON logentry (account_id, datetime);
CREATE INDEX logentry_datetime ON logentry (datetime);
CREATE INDEX logentry_kind_id ON logentry (kind_id);
CREATE INDEX logentry_performer_id ON logentry (performer_id);
CREATE INDEX logentry_performer_id_datetime ON logentry (performer_id, datetime);
CREATE INDEX logentry_repository_id ON logentry (repository_id);
CREATE INDEX logentry_repository_id_datetime ON logentry (repository_id, datetime);
CREATE INDEX logentry_repository_id_datetime_kind_id ON logentry (repository_id, datetime, kind_id);
CREATE INDEX logentry2_account_id ON logentry2 (account_id);
CREATE INDEX logentry2_account_id_datetime ON logentry2 (account_id, datetime);
CREATE INDEX logentry2_datetime ON logentry2 (datetime);
CREATE INDEX logentry2_kind_id ON logentry2 (kind_id);
CREATE INDEX logentry2_performer_id ON logentry2 (performer_id);
CREATE INDEX logentry2_performer_id_datetime ON logentry2 (performer_id, datetime);
CREATE INDEX logentry2_repository_id ON logentry2 (repository_id);
CREATE INDEX logentry2_repository_id_datetime ON logentry2 (repository_id, datetime);
CREATE INDEX logentry2_repository_id_datetime_kind_id ON logentry2 (repository_id, datetime, kind_id);
CREATE INDEX messages_media_type_id ON messages (media_type_id);
CREATE INDEX messages_severity ON messages (severity);
CREATE INDEX messages_uuid ON messages (uuid);
CREATE INDEX namespaceautoprunepolicy_namespace_id ON namespaceautoprunepolicy (namespace_id);
CREATE INDEX namespaceautoprunepolicy_uuid ON namespaceautoprunepolicy (uuid);
CREATE INDEX namespaceimmutabilitypolicy_namespace_id ON namespaceimmutabilitypolicy (namespace_id);
CREATE UNIQUE INDEX namespaceimmutabilitypolicy_uuid ON namespaceimmutabilitypolicy (uuid);
CREATE INDEX notification_created ON notification (created);
CREATE INDEX notification_kind_id ON notification (kind_id);
CREATE INDEX notification_lookup_path ON notification (lookup_path);
CREATE INDEX notification_target_id ON notification (target_id);
CREATE INDEX notification_uuid ON notification (uuid);
CREATE INDEX oauthapplication_client_id ON oauthapplication (client_id);
CREATE INDEX oauthapplication_organization_id ON oauthapplication (organization_id);
CREATE INDEX organizationcontactemail_contact_email ON organizationcontactemail (contact_email);
CREATE UNIQUE INDEX organizationcontactemail_organization_id ON organizationcontactemail (organization_id);
CREATE INDEX organizationrhskus_org_id ON organizationrhskus (org_id);
CREATE INDEX organizationrhskus_quantity ON organizationrhskus (quantity);
CREATE INDEX organizationrhskus_subscription_id ON organizationrhskus (subscription_id);
CREATE INDEX organizationrhskus_user_id ON organizationrhskus (user_id);
CREATE INDEX orgmirrorconfig_external_registry_type ON orgmirrorconfig (external_registry_type);
CREATE INDEX orgmirrorconfig_internal_robot_id ON orgmirrorconfig (internal_robot_id);
CREATE INDEX orgmirrorconfig_mirror_type ON orgmirrorconfig (mirror_type);
CREATE UNIQUE INDEX orgmirrorconfig_organization_id ON orgmirrorconfig (organization_id);
CREATE INDEX orgmirrorconfig_sync_status ON orgmirrorconfig (sync_status);
CREATE INDEX orgmirrorconfig_visibility_id ON orgmirrorconfig (visibility_id);
CREATE INDEX proxycacheconfig_organization_id ON proxycacheconfig (organization_id);
CREATE INDEX quayrelease_created ON quayrelease (created);
CREATE INDEX quayrelease_region_id ON quayrelease (region_id);
CREATE INDEX quayrelease_service_id ON quayrelease (service_id);
CREATE INDEX quayrelease_service_id_region_id_created ON quayrelease (service_id, region_id, created);
CREATE UNIQUE INDEX quayrelease_service_id_version_region_id ON quayrelease (service_id, version, region_id);
CREATE INDEX quotanamespacesize_backfill_start_ms ON quotanamespacesize (backfill_start_ms);
CREATE UNIQUE INDEX quotanamespacesize_namespace_user_id ON quotanamespacesize (namespace_user_id);
CREATE INDEX quotanamespacesize_size_bytes ON quotanamespacesize (size_bytes);
CREATE UNIQUE INDEX redhatsubscriptions_account_number ON redhatsubscriptions (account_number);
CREATE INDEX redhatsubscriptions_user_id ON redhatsubscriptions (user_id);
CREATE INDEX repository_description__fulltext ON repository (description);
CREATE INDEX repository_kind_id ON repository (kind_id);
CREATE INDEX repository_name__fulltext ON repository (name);
CREATE INDEX repository_namespace_user_id ON repository (namespace_user_id);
CREATE UNIQUE INDEX repository_namespace_user_id_name ON repository (namespace_user_id, name);
CREATE INDEX repository_state ON repository (state);
CREATE INDEX repository_visibility_id ON repository (visibility_id);
CREATE UNIQUE INDEX robotaccountmetadata_robot_account_id ON robotaccountmetadata (robot_account_id);
CREATE UNIQUE INDEX robotaccounttoken_robot_account_id ON robotaccounttoken (robot_account_id);
CREATE INDEX servicekeyapproval_approval_type ON servicekeyapproval (approval_type);
CREATE INDEX servicekeyapproval_approver_id ON servicekeyapproval (approver_id);
CREATE INDEX team_name ON team (name);
CREATE UNIQUE INDEX team_name_organization_id ON team (name, organization_id);
CREATE INDEX team_organization_id ON team (organization_id);
CREATE INDEX team_role_id ON team (role_id);
CREATE UNIQUE INDEX userorganizationquota_namespace_id ON userorganizationquota (namespace_id);
CREATE INDEX userprompt_kind_id ON userprompt (kind_id);
CREATE INDEX userprompt_user_id ON userprompt (user_id);
CREATE UNIQUE INDEX userprompt_user_id_kind_id ON userprompt (user_id, kind_id);
CREATE INDEX userregion_location_id ON userregion (location_id);
CREATE INDEX userregion_user_id ON userregion (user_id);
CREATE INDEX accesstoken_kind_id ON accesstoken (kind_id);
CREATE INDEX accesstoken_repository_id ON accesstoken (repository_id);
CREATE INDEX accesstoken_role_id ON accesstoken (role_id);
CREATE UNIQUE INDEX accesstoken_token_name ON accesstoken (token_name);
CREATE INDEX blobupload_created ON blobupload (created);
CREATE INDEX blobupload_location_id ON blobupload (location_id);
CREATE INDEX blobupload_repository_id ON blobupload (repository_id);
CREATE UNIQUE INDEX blobupload_repository_id_uuid ON blobupload (repository_id, uuid);
CREATE UNIQUE INDEX blobupload_uuid ON blobupload (uuid);
CREATE INDEX deletedrepository_original_name ON deletedrepository (original_name);
CREATE INDEX deletedrepository_queue_id ON deletedrepository (queue_id);
CREATE UNIQUE INDEX deletedrepository_repository_id ON deletedrepository (repository_id);
CREATE INDEX manifest_artifact_type_backfilled ON manifest (artifact_type_backfilled);
CREATE INDEX manifest_digest ON manifest (digest);
CREATE INDEX manifest_media_type_id ON manifest (media_type_id);
CREATE INDEX manifest_repository_id ON manifest (repository_id);
CREATE INDEX manifest_repository_id_artifact_type ON manifest (repository_id, artifact_type);
CREATE INDEX manifest_repository_id_config_media_type ON manifest (repository_id, config_media_type);
CREATE UNIQUE INDEX manifest_repository_id_digest ON manifest (repository_id, digest);
CREATE INDEX manifest_repository_id_media_type_id ON manifest (repository_id, media_type_id);
CREATE INDEX manifest_repository_id_subject ON manifest (repository_id, subject);
CREATE INDEX manifest_subject_backfilled ON manifest (subject_backfilled);
CREATE INDEX manifestpullstatistics_repository_id ON manifestpullstatistics (repository_id);
CREATE UNIQUE INDEX manifestpullstatistics_repository_id_manifest_digest ON manifestpullstatistics (repository_id, manifest_digest);
CREATE INDEX oauthaccesstoken_application_id ON oauthaccesstoken (application_id);
CREATE INDEX oauthaccesstoken_authorized_user_id ON oauthaccesstoken (authorized_user_id);
CREATE UNIQUE INDEX oauthaccesstoken_token_name ON oauthaccesstoken (token_name);
CREATE INDEX oauthaccesstoken_uuid ON oauthaccesstoken (uuid);
CREATE INDEX oauthassignedtoken_application_id ON oauthassignedtoken (application_id);
CREATE INDEX oauthassignedtoken_assigned_user_id ON oauthassignedtoken (assigned_user_id);
CREATE UNIQUE INDEX oauthassignedtoken_uuid ON oauthassignedtoken (uuid);
CREATE INDEX oauthauthorizationcode_application_id ON oauthauthorizationcode (application_id);
CREATE UNIQUE INDEX oauthauthorizationcode_code_name ON oauthauthorizationcode (code_name);
CREATE INDEX orgmirrorrepository_org_mirror_config_id ON orgmirrorrepository (org_mirror_config_id);
CREATE UNIQUE INDEX orgmirrorrepository_org_mirror_config_id_repository_name ON orgmirrorrepository (org_mirror_config_id, repository_name);
CREATE INDEX orgmirrorrepository_org_mirror_config_id_sync_status ON orgmirrorrepository (org_mirror_config_id, sync_status);
CREATE INDEX orgmirrorrepository_repository_id ON orgmirrorrepository (repository_id);
CREATE INDEX orgmirrorrepository_sync_status ON orgmirrorrepository (sync_status);
CREATE INDEX permissionprototype_activating_user_id ON permissionprototype (activating_user_id);
CREATE INDEX permissionprototype_delegate_team_id ON permissionprototype (delegate_team_id);
CREATE INDEX permissionprototype_delegate_user_id ON permissionprototype (delegate_user_id);
CREATE INDEX permissionprototype_org_id ON permissionprototype (org_id);
CREATE INDEX permissionprototype_org_id_activating_user_id ON permissionprototype (org_id, activating_user_id);
CREATE INDEX permissionprototype_role_id ON permissionprototype (role_id);
CREATE INDEX permissionprototype_uuid ON permissionprototype (uuid);
CREATE INDEX quotalimits_quota_id ON quotalimits (quota_id);
CREATE INDEX quotalimits_quota_type_id ON quotalimits (quota_type_id);
CREATE UNIQUE INDEX quotarepositorysize_repository_id ON quotarepositorysize (repository_id);
CREATE INDEX quotarepositorysize_size_bytes ON quotarepositorysize (size_bytes);
CREATE INDEX repomirrorrule_left_child_id ON repomirrorrule (left_child_id);
CREATE INDEX repomirrorrule_repository_id ON repomirrorrule (repository_id);
CREATE INDEX repomirrorrule_right_child_id ON repomirrorrule (right_child_id);
CREATE INDEX repomirrorrule_rule_type ON repomirrorrule (rule_type);
CREATE INDEX repomirrorrule_uuid ON repomirrorrule (uuid);
CREATE INDEX repositoryactioncount_date ON repositoryactioncount (date);
CREATE INDEX repositoryactioncount_repository_id ON repositoryactioncount (repository_id);
CREATE UNIQUE INDEX repositoryactioncount_repository_id_date ON repositoryactioncount (repository_id, date);
CREATE UNIQUE INDEX repositoryauthorizedemail_code ON repositoryauthorizedemail (code);
CREATE UNIQUE INDEX repositoryauthorizedemail_email_repository_id ON repositoryauthorizedemail (email, repository_id);
CREATE INDEX repositoryauthorizedemail_repository_id ON repositoryauthorizedemail (repository_id);
CREATE INDEX repositoryautoprunepolicy_namespace_id ON repositoryautoprunepolicy (namespace_id);
CREATE INDEX repositoryautoprunepolicy_repository_id ON repositoryautoprunepolicy (repository_id);
CREATE INDEX repositoryautoprunepolicy_uuid ON repositoryautoprunepolicy (uuid);
CREATE INDEX repositoryimmutabilitypolicy_namespace_id ON repositoryimmutabilitypolicy (namespace_id);
CREATE INDEX repositoryimmutabilitypolicy_repository_id ON repositoryimmutabilitypolicy (repository_id);
CREATE UNIQUE INDEX repositoryimmutabilitypolicy_uuid ON repositoryimmutabilitypolicy (uuid);
CREATE INDEX repositorynotification_event_id ON repositorynotification (event_id);
CREATE INDEX repositorynotification_last_ran_ms ON repositorynotification (last_ran_ms);
CREATE INDEX repositorynotification_method_id ON repositorynotification (method_id);
CREATE INDEX repositorynotification_repository_id ON repositorynotification (repository_id);
CREATE INDEX repositorynotification_uuid ON repositorynotification (uuid);
CREATE INDEX repositorypermission_repository_id ON repositorypermission (repository_id);
CREATE INDEX repositorypermission_role_id ON repositorypermission (role_id);
CREATE INDEX repositorypermission_team_id ON repositorypermission (team_id);
CREATE UNIQUE INDEX repositorypermission_team_id_repository_id ON repositorypermission (team_id, repository_id);
CREATE INDEX repositorypermission_user_id ON repositorypermission (user_id);
CREATE UNIQUE INDEX repositorypermission_user_id_repository_id ON repositorypermission (user_id, repository_id);
CREATE UNIQUE INDEX repositorysearchscore_repository_id ON repositorysearchscore (repository_id);
CREATE INDEX repositorysearchscore_score ON repositorysearchscore (score);
CREATE INDEX servicekey_approval_id ON servicekey (approval_id);
CREATE UNIQUE INDEX servicekey_kid ON servicekey (kid);
CREATE INDEX servicekey_service ON servicekey (service);
CREATE INDEX star_repository_id ON star (repository_id);
CREATE INDEX star_user_id ON star (user_id);
CREATE UNIQUE INDEX star_user_id_repository_id ON star (user_id, repository_id);
CREATE INDEX tagpullstatistics_repository_id ON tagpullstatistics (repository_id);
CREATE UNIQUE INDEX tagpullstatistics_repository_id_tag_name ON tagpullstatistics (repository_id, tag_name);
CREATE INDEX teammember_team_id ON teammember (team_id);
CREATE INDEX teammember_user_id ON teammember (user_id);
CREATE UNIQUE INDEX teammember_user_id_team_id ON teammember (user_id, team_id);
CREATE INDEX teammemberinvite_inviter_id ON teammemberinvite (inviter_id);
CREATE INDEX teammemberinvite_team_id ON teammemberinvite (team_id);
CREATE INDEX teammemberinvite_user_id ON teammemberinvite (user_id);
CREATE INDEX teamsync_last_updated ON teamsync (last_updated);
CREATE INDEX teamsync_service_id ON teamsync (service_id);
CREATE UNIQUE INDEX teamsync_team_id ON teamsync (team_id);
CREATE INDEX uploadedblob_blob_id ON uploadedblob (blob_id);
CREATE INDEX uploadedblob_expires_at ON uploadedblob (expires_at);
CREATE INDEX uploadedblob_repository_id ON uploadedblob (repository_id);
CREATE INDEX manifestblob_blob_id ON manifestblob (blob_id);
CREATE INDEX manifestblob_manifest_id ON manifestblob (manifest_id);
CREATE UNIQUE INDEX manifestblob_manifest_id_blob_id ON manifestblob (manifest_id, blob_id);
CREATE INDEX manifestblob_repository_id ON manifestblob (repository_id);
CREATE INDEX manifestchild_child_manifest_id ON manifestchild (child_manifest_id);
CREATE INDEX manifestchild_manifest_id ON manifestchild (manifest_id);
CREATE UNIQUE INDEX manifestchild_manifest_id_child_manifest_id ON manifestchild (manifest_id, child_manifest_id);
CREATE INDEX manifestchild_repository_id ON manifestchild (repository_id);
CREATE INDEX manifestchild_repository_id_child_manifest_id ON manifestchild (repository_id, child_manifest_id);
CREATE INDEX manifestchild_repository_id_manifest_id ON manifestchild (repository_id, manifest_id);
CREATE INDEX manifestchild_repository_id_manifest_id_child_manifest_id ON manifestchild (repository_id, manifest_id, child_manifest_id);
CREATE INDEX manifestlabel_label_id ON manifestlabel (label_id);
CREATE INDEX manifestlabel_manifest_id ON manifestlabel (manifest_id);
CREATE UNIQUE INDEX manifestlabel_manifest_id_label_id ON manifestlabel (manifest_id, label_id);
CREATE INDEX manifestlabel_repository_id ON manifestlabel (repository_id);
CREATE INDEX manifestsecuritystatus_index_status ON manifestsecuritystatus (index_status);
CREATE INDEX manifestsecuritystatus_indexer_hash ON manifestsecuritystatus (indexer_hash);
CREATE INDEX manifestsecuritystatus_indexer_version ON manifestsecuritystatus (indexer_version);
CREATE INDEX manifestsecuritystatus_last_indexed ON manifestsecuritystatus (last_indexed);
CREATE UNIQUE INDEX manifestsecuritystatus_manifest_id ON manifestsecuritystatus (manifest_id);
CREATE INDEX manifestsecuritystatus_repository_id ON manifestsecuritystatus (repository_id);
CREATE INDEX repomirrorconfig_internal_robot_id ON repomirrorconfig (internal_robot_id);
CREATE INDEX repomirrorconfig_mirror_type ON repomirrorconfig (mirror_type);
CREATE UNIQUE INDEX repomirrorconfig_repository_id ON repomirrorconfig (repository_id);
CREATE INDEX repomirrorconfig_root_rule_id ON repomirrorconfig (root_rule_id);
CREATE INDEX repomirrorconfig_sync_status ON repomirrorconfig (sync_status);
CREATE INDEX repositorybuildtrigger_connected_user_id ON repositorybuildtrigger (connected_user_id);
CREATE INDEX repositorybuildtrigger_disabled_datetime ON repositorybuildtrigger (disabled_datetime);
CREATE INDEX repositorybuildtrigger_disabled_reason_id ON repositorybuildtrigger (disabled_reason_id);
CREATE INDEX repositorybuildtrigger_pull_robot_id ON repositorybuildtrigger (pull_robot_id);
CREATE INDEX repositorybuildtrigger_repository_id ON repositorybuildtrigger (repository_id);
CREATE INDEX repositorybuildtrigger_service_id ON repositorybuildtrigger (service_id);
CREATE INDEX repositorybuildtrigger_uuid ON repositorybuildtrigger (uuid);
CREATE INDEX repositorybuildtrigger_write_token_id ON repositorybuildtrigger (write_token_id);
CREATE INDEX tag_lifetime_end_ms ON tag (lifetime_end_ms);
CREATE INDEX tag_linked_tag_id ON tag (linked_tag_id);
CREATE INDEX tag_manifest_id ON tag (manifest_id);
CREATE INDEX tag_manifest_id_immutable ON tag (manifest_id, immutable);
CREATE INDEX tag_manifest_id_lifetime_end_ms ON tag (manifest_id, lifetime_end_ms);
CREATE INDEX tag_repository_id ON tag (repository_id);
CREATE INDEX tag_repository_id_immutable ON tag (repository_id, immutable);
CREATE INDEX tag_repository_id_lifetime_end_ms ON tag (repository_id, lifetime_end_ms);
CREATE INDEX tag_repository_id_lifetime_start_ms ON tag (repository_id, lifetime_start_ms);
CREATE INDEX tag_repository_id_name ON tag (repository_id, name);
CREATE INDEX tag_repository_id_name_hidden ON tag (repository_id, name, hidden);
CREATE UNIQUE INDEX tag_repository_id_name_lifetime_end_ms ON tag (repository_id, name, lifetime_end_ms);
CREATE INDEX tag_repository_id_name_tag_kind_id ON tag (repository_id, name, tag_kind_id);
CREATE INDEX tag_tag_kind_id ON tag (tag_kind_id);
CREATE INDEX repositorybuild_access_token_id ON repositorybuild (access_token_id);
CREATE INDEX repositorybuild_logs_archived ON repositorybuild (logs_archived);
CREATE INDEX repositorybuild_pull_robot_id ON repositorybuild (pull_robot_id);
CREATE INDEX repositorybuild_queue_id ON repositorybuild (queue_id);
CREATE INDEX repositorybuild_repository_id ON repositorybuild (repository_id);
CREATE INDEX repositorybuild_repository_id_started_phase ON repositorybuild (repository_id, started, phase);
CREATE INDEX repositorybuild_resource_key ON repositorybuild (resource_key);
CREATE INDEX repositorybuild_started ON repositorybuild (started);
CREATE INDEX repositorybuild_started_logs_archived_phase ON repositorybuild (started, logs_archived, phase);
CREATE INDEX repositorybuild_trigger_id ON repositorybuild (trigger_id);
CREATE INDEX repositorybuild_uuid ON repositorybuild (uuid);
CREATE INDEX tagnotificationsuccess_method_id ON tagnotificationsuccess (method_id);
CREATE INDEX tagnotificationsuccess_notification_id ON tagnotificationsuccess (notification_id);
CREATE INDEX tagnotificationsuccess_tag_id ON tagnotificationsuccess (tag_id);
