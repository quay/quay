-- Artifact-derived OMR v2.0.11 SQLite fixture at Alembic revision
-- 3f8d7acdf7f9. Extracted from a real mirror-registry-offline v2.0.11
-- install (registry.redhat.io/quay/quay-rhel8:v3.12.18); see the commit
-- that added this file for full provenance (release/image digests,
-- extraction procedure, sanitized columns). Contains only synthetic
-- install-time data plus 3 small test tags pushed for RunBridge's
-- convergence tests in fixture_test.go; secret-bearing columns were
-- replaced with fixed placeholder values before this dump was taken.
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version VALUES('3f8d7acdf7f9');
CREATE TABLE accesstokenkind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_accesstokenkind PRIMARY KEY (id)
);
INSERT INTO accesstokenkind VALUES(1,'build-worker');
INSERT INTO accesstokenkind VALUES(2,'pushpull-token');
CREATE TABLE buildtriggerservice (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_buildtriggerservice PRIMARY KEY (id)
);
INSERT INTO buildtriggerservice VALUES(1,'github');
INSERT INTO buildtriggerservice VALUES(2,'gitlab');
INSERT INTO buildtriggerservice VALUES(3,'bitbucket');
INSERT INTO buildtriggerservice VALUES(4,'custom-git');
CREATE TABLE externalnotificationevent (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_externalnotificationevent PRIMARY KEY (id)
);
INSERT INTO externalnotificationevent VALUES(1,'build_failure');
INSERT INTO externalnotificationevent VALUES(2,'build_queued');
INSERT INTO externalnotificationevent VALUES(3,'build_start');
INSERT INTO externalnotificationevent VALUES(4,'build_success');
INSERT INTO externalnotificationevent VALUES(5,'repo_push');
INSERT INTO externalnotificationevent VALUES(6,'vulnerability_found');
INSERT INTO externalnotificationevent VALUES(7,'build_cancelled');
INSERT INTO externalnotificationevent VALUES(8,'repo_mirror_sync_started');
INSERT INTO externalnotificationevent VALUES(9,'repo_mirror_sync_success');
INSERT INTO externalnotificationevent VALUES(10,'repo_mirror_sync_failed');
INSERT INTO externalnotificationevent VALUES(11,'repo_image_expiry');
CREATE TABLE externalnotificationmethod (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_externalnotificationmethod PRIMARY KEY (id)
);
INSERT INTO externalnotificationmethod VALUES(1,'email');
INSERT INTO externalnotificationmethod VALUES(2,'flowdock');
INSERT INTO externalnotificationmethod VALUES(3,'hipchat');
INSERT INTO externalnotificationmethod VALUES(4,'quay_notification');
INSERT INTO externalnotificationmethod VALUES(5,'slack');
INSERT INTO externalnotificationmethod VALUES(6,'webhook');
CREATE TABLE imagestoragelocation (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_imagestoragelocation PRIMARY KEY (id)
);
INSERT INTO imagestoragelocation VALUES(1,'s3_us_east_1');
INSERT INTO imagestoragelocation VALUES(2,'s3_eu_west_1');
INSERT INTO imagestoragelocation VALUES(3,'s3_ap_southeast_1');
INSERT INTO imagestoragelocation VALUES(4,'s3_ap_southeast_2');
INSERT INTO imagestoragelocation VALUES(5,'s3_ap_northeast_1');
INSERT INTO imagestoragelocation VALUES(6,'s3_sa_east_1');
INSERT INTO imagestoragelocation VALUES(7,'local');
INSERT INTO imagestoragelocation VALUES(8,'s3_us_west_1');
INSERT INTO imagestoragelocation VALUES(9,'default');
CREATE TABLE imagestoragesignaturekind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_imagestoragesignaturekind PRIMARY KEY (id)
);
INSERT INTO imagestoragesignaturekind VALUES(1,'gpg2');
CREATE TABLE imagestoragetransformation (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_imagestoragetransformation PRIMARY KEY (id)
);
INSERT INTO imagestoragetransformation VALUES(1,'squash');
INSERT INTO imagestoragetransformation VALUES(2,'aci');
CREATE TABLE labelsourcetype (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	mutable BOOLEAN NOT NULL,
	CONSTRAINT pk_labelsourcetype PRIMARY KEY (id)
);
INSERT INTO labelsourcetype VALUES(1,'manifest',0);
INSERT INTO labelsourcetype VALUES(2,'api',1);
INSERT INTO labelsourcetype VALUES(3,'internal',0);
CREATE TABLE logentrykind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_logentrykind PRIMARY KEY (id)
);
INSERT INTO logentrykind VALUES(1,'account_change_cc');
INSERT INTO logentrykind VALUES(2,'account_change_password');
INSERT INTO logentrykind VALUES(3,'account_change_plan');
INSERT INTO logentrykind VALUES(4,'account_convert');
INSERT INTO logentrykind VALUES(5,'add_repo_accesstoken');
INSERT INTO logentrykind VALUES(6,'add_repo_notification');
INSERT INTO logentrykind VALUES(7,'add_repo_permission');
INSERT INTO logentrykind VALUES(8,'add_repo_webhook');
INSERT INTO logentrykind VALUES(9,'build_dockerfile');
INSERT INTO logentrykind VALUES(10,'change_repo_permission');
INSERT INTO logentrykind VALUES(11,'change_repo_visibility');
INSERT INTO logentrykind VALUES(12,'create_application');
INSERT INTO logentrykind VALUES(13,'create_prototype_permission');
INSERT INTO logentrykind VALUES(14,'create_repo');
INSERT INTO logentrykind VALUES(15,'create_robot');
INSERT INTO logentrykind VALUES(16,'create_tag');
INSERT INTO logentrykind VALUES(17,'delete_application');
INSERT INTO logentrykind VALUES(18,'delete_prototype_permission');
INSERT INTO logentrykind VALUES(19,'delete_repo');
INSERT INTO logentrykind VALUES(20,'delete_repo_accesstoken');
INSERT INTO logentrykind VALUES(21,'delete_repo_notification');
INSERT INTO logentrykind VALUES(22,'delete_repo_permission');
INSERT INTO logentrykind VALUES(23,'delete_repo_trigger');
INSERT INTO logentrykind VALUES(24,'delete_repo_webhook');
INSERT INTO logentrykind VALUES(25,'delete_robot');
INSERT INTO logentrykind VALUES(26,'delete_tag');
INSERT INTO logentrykind VALUES(27,'manifest_label_add');
INSERT INTO logentrykind VALUES(28,'manifest_label_delete');
INSERT INTO logentrykind VALUES(29,'modify_prototype_permission');
INSERT INTO logentrykind VALUES(30,'move_tag');
INSERT INTO logentrykind VALUES(31,'org_add_team_member');
INSERT INTO logentrykind VALUES(32,'org_create_team');
INSERT INTO logentrykind VALUES(33,'org_delete_team');
INSERT INTO logentrykind VALUES(34,'org_delete_team_member_invite');
INSERT INTO logentrykind VALUES(35,'org_invite_team_member');
INSERT INTO logentrykind VALUES(36,'org_remove_team_member');
INSERT INTO logentrykind VALUES(37,'org_set_team_description');
INSERT INTO logentrykind VALUES(38,'org_set_team_role');
INSERT INTO logentrykind VALUES(39,'org_team_member_invite_accepted');
INSERT INTO logentrykind VALUES(40,'org_team_member_invite_declined');
INSERT INTO logentrykind VALUES(41,'pull_repo');
INSERT INTO logentrykind VALUES(42,'push_repo');
INSERT INTO logentrykind VALUES(43,'regenerate_robot_token');
INSERT INTO logentrykind VALUES(44,'repo_verb');
INSERT INTO logentrykind VALUES(45,'reset_application_client_secret');
INSERT INTO logentrykind VALUES(46,'revert_tag');
INSERT INTO logentrykind VALUES(47,'service_key_approve');
INSERT INTO logentrykind VALUES(48,'service_key_create');
INSERT INTO logentrykind VALUES(49,'service_key_delete');
INSERT INTO logentrykind VALUES(50,'service_key_extend');
INSERT INTO logentrykind VALUES(51,'service_key_modify');
INSERT INTO logentrykind VALUES(52,'service_key_rotate');
INSERT INTO logentrykind VALUES(53,'setup_repo_trigger');
INSERT INTO logentrykind VALUES(54,'set_repo_description');
INSERT INTO logentrykind VALUES(55,'take_ownership');
INSERT INTO logentrykind VALUES(56,'update_application');
INSERT INTO logentrykind VALUES(57,'change_repo_trust');
INSERT INTO logentrykind VALUES(58,'reset_repo_notification');
INSERT INTO logentrykind VALUES(59,'change_tag_expiration');
INSERT INTO logentrykind VALUES(60,'create_app_specific_token');
INSERT INTO logentrykind VALUES(61,'revoke_app_specific_token');
INSERT INTO logentrykind VALUES(62,'toggle_repo_trigger');
INSERT INTO logentrykind VALUES(63,'repo_mirror_enabled');
INSERT INTO logentrykind VALUES(64,'repo_mirror_disabled');
INSERT INTO logentrykind VALUES(65,'repo_mirror_config_changed');
INSERT INTO logentrykind VALUES(66,'repo_mirror_sync_started');
INSERT INTO logentrykind VALUES(67,'repo_mirror_sync_failed');
INSERT INTO logentrykind VALUES(68,'repo_mirror_sync_success');
INSERT INTO logentrykind VALUES(69,'repo_mirror_sync_now_requested');
INSERT INTO logentrykind VALUES(70,'repo_mirror_sync_tag_success');
INSERT INTO logentrykind VALUES(71,'repo_mirror_sync_tag_failed');
INSERT INTO logentrykind VALUES(72,'repo_mirror_sync_test_success');
INSERT INTO logentrykind VALUES(73,'repo_mirror_sync_test_failed');
INSERT INTO logentrykind VALUES(74,'repo_mirror_sync_test_started');
INSERT INTO logentrykind VALUES(75,'change_repo_state');
INSERT INTO logentrykind VALUES(76,'create_proxy_cache_config');
INSERT INTO logentrykind VALUES(77,'delete_proxy_cache_config');
INSERT INTO logentrykind VALUES(78,'start_build_trigger');
INSERT INTO logentrykind VALUES(79,'cancel_build');
INSERT INTO logentrykind VALUES(80,'org_create');
INSERT INTO logentrykind VALUES(81,'org_delete');
INSERT INTO logentrykind VALUES(82,'org_change_email');
INSERT INTO logentrykind VALUES(83,'org_change_invoicing');
INSERT INTO logentrykind VALUES(84,'org_change_tag_expiration');
INSERT INTO logentrykind VALUES(85,'org_change_name');
INSERT INTO logentrykind VALUES(86,'user_create');
INSERT INTO logentrykind VALUES(87,'user_delete');
INSERT INTO logentrykind VALUES(88,'user_disable');
INSERT INTO logentrykind VALUES(89,'user_enable');
INSERT INTO logentrykind VALUES(90,'user_change_email');
INSERT INTO logentrykind VALUES(91,'user_change_password');
INSERT INTO logentrykind VALUES(92,'user_change_name');
INSERT INTO logentrykind VALUES(93,'user_change_invoicing');
INSERT INTO logentrykind VALUES(94,'user_change_tag_expiration');
INSERT INTO logentrykind VALUES(95,'user_change_metadata');
INSERT INTO logentrykind VALUES(96,'user_generate_client_key');
INSERT INTO logentrykind VALUES(97,'login_success');
INSERT INTO logentrykind VALUES(98,'logout_success');
INSERT INTO logentrykind VALUES(99,'permanently_delete_tag');
INSERT INTO logentrykind VALUES(100,'autoprune_tag_delete');
INSERT INTO logentrykind VALUES(101,'create_namespace_autoprune_policy');
INSERT INTO logentrykind VALUES(102,'update_namespace_autoprune_policy');
INSERT INTO logentrykind VALUES(103,'delete_namespace_autoprune_policy');
INSERT INTO logentrykind VALUES(104,'login_failure');
INSERT INTO logentrykind VALUES(105,'push_repo_failed');
INSERT INTO logentrykind VALUES(106,'pull_repo_failed');
INSERT INTO logentrykind VALUES(107,'delete_tag_failed');
INSERT INTO logentrykind VALUES(108,'create_repository_autoprune_policy');
INSERT INTO logentrykind VALUES(109,'update_repository_autoprune_policy');
INSERT INTO logentrykind VALUES(110,'delete_repository_autoprune_policy');
INSERT INTO logentrykind VALUES(111,'enable_team_sync');
INSERT INTO logentrykind VALUES(112,'disable_team_sync');
INSERT INTO logentrykind VALUES(113,'oauth_token_assigned');
INSERT INTO logentrykind VALUES(114,'oauth_token_revoked');
CREATE TABLE loginservice (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_loginservice PRIMARY KEY (id)
);
INSERT INTO loginservice VALUES(1,'github');
INSERT INTO loginservice VALUES(2,'quayrobot');
INSERT INTO loginservice VALUES(3,'ldap');
INSERT INTO loginservice VALUES(4,'google');
INSERT INTO loginservice VALUES(5,'keystone');
INSERT INTO loginservice VALUES(6,'dex');
INSERT INTO loginservice VALUES(7,'jwtauthn');
INSERT INTO loginservice VALUES(8,'oidc');
CREATE TABLE mediatype (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_mediatype PRIMARY KEY (id)
);
INSERT INTO mediatype VALUES(1,'text/plain');
INSERT INTO mediatype VALUES(2,'application/json');
INSERT INTO mediatype VALUES(3,'text/markdown');
INSERT INTO mediatype VALUES(4,'application/vnd.cnr.blob.v0.tar+gzip');
INSERT INTO mediatype VALUES(5,'application/vnd.cnr.package-manifest.helm.v0.json');
INSERT INTO mediatype VALUES(6,'application/vnd.cnr.package-manifest.kpm.v0.json');
INSERT INTO mediatype VALUES(7,'application/vnd.cnr.package-manifest.docker-compose.v0.json');
INSERT INTO mediatype VALUES(8,'application/vnd.cnr.package.kpm.v0.tar+gzip');
INSERT INTO mediatype VALUES(9,'application/vnd.cnr.package.helm.v0.tar+gzip');
INSERT INTO mediatype VALUES(10,'application/vnd.cnr.package.docker-compose.v0.tar+gzip');
INSERT INTO mediatype VALUES(11,'application/vnd.cnr.manifests.v0.json');
INSERT INTO mediatype VALUES(12,'application/vnd.cnr.manifest.list.v0.json');
INSERT INTO mediatype VALUES(13,'application/vnd.docker.distribution.manifest.v1+json');
INSERT INTO mediatype VALUES(14,'application/vnd.docker.distribution.manifest.v1+prettyjws');
INSERT INTO mediatype VALUES(15,'application/vnd.docker.distribution.manifest.list.v2+json');
INSERT INTO mediatype VALUES(16,'application/vnd.docker.distribution.manifest.v2+json');
INSERT INTO mediatype VALUES(17,'application/vnd.oci.image.manifest.v1+json');
INSERT INTO mediatype VALUES(18,'application/vnd.oci.image.index.v1+json');
CREATE TABLE notificationkind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_notificationkind PRIMARY KEY (id)
);
INSERT INTO notificationkind VALUES(1,'build_failure');
INSERT INTO notificationkind VALUES(2,'build_queued');
INSERT INTO notificationkind VALUES(3,'build_start');
INSERT INTO notificationkind VALUES(4,'build_success');
INSERT INTO notificationkind VALUES(5,'expiring_license');
INSERT INTO notificationkind VALUES(6,'maintenance');
INSERT INTO notificationkind VALUES(7,'org_team_invite');
INSERT INTO notificationkind VALUES(8,'over_private_usage');
INSERT INTO notificationkind VALUES(9,'password_required');
INSERT INTO notificationkind VALUES(10,'repo_push');
INSERT INTO notificationkind VALUES(11,'service_key_submitted');
INSERT INTO notificationkind VALUES(12,'vulnerability_found');
INSERT INTO notificationkind VALUES(13,'build_cancelled');
INSERT INTO notificationkind VALUES(14,'repo_mirror_sync_started');
INSERT INTO notificationkind VALUES(15,'repo_mirror_sync_success');
INSERT INTO notificationkind VALUES(16,'repo_mirror_sync_failed');
INSERT INTO notificationkind VALUES(17,'quota_warning');
INSERT INTO notificationkind VALUES(18,'quota_error');
INSERT INTO notificationkind VALUES(19,'assigned_authorization');
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
	retries_remaining INTEGER NOT NULL, state_id VARCHAR(255) DEFAULT '' NOT NULL,
	CONSTRAINT pk_queueitem PRIMARY KEY (id)
);
CREATE TABLE role (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_role PRIMARY KEY (id)
);
INSERT INTO role VALUES(1,'admin');
INSERT INTO role VALUES(2,'write');
INSERT INTO role VALUES(3,'read');
CREATE TABLE servicekeyapproval (
	id INTEGER NOT NULL,
	approver_id INTEGER,
	approval_type VARCHAR(255) NOT NULL,
	approved_date DATETIME NOT NULL,
	notes TEXT NOT NULL,
	CONSTRAINT pk_servicekeyapproval PRIMARY KEY (id)
);
INSERT INTO servicekeyapproval VALUES(1,NULL,'ServiceKeyApprovalType.AUTOMATIC','2026-07-31 12:36:21.590680','');
CREATE TABLE teamrole (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_teamrole PRIMARY KEY (id)
);
INSERT INTO teamrole VALUES(1,'admin');
INSERT INTO teamrole VALUES(2,'creator');
INSERT INTO teamrole VALUES(3,'member');
CREATE TABLE visibility (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_visibility PRIMARY KEY (id)
);
INSERT INTO visibility VALUES(1,'public');
INSERT INTO visibility VALUES(2,'private');
CREATE TABLE emailconfirmation (
	id INTEGER NOT NULL,
	code VARCHAR(255) NOT NULL,
	user_id INTEGER NOT NULL,
	pw_reset BOOLEAN NOT NULL,
	new_email VARCHAR(255),
	email_confirm BOOLEAN NOT NULL,
	created DATETIME NOT NULL, verification_code VARCHAR(255),
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
	CONSTRAINT fk_federatedlogin_service_id_loginservice FOREIGN KEY(service_id) REFERENCES loginservice (id),
	CONSTRAINT fk_federatedlogin_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE imagestorageplacement (
	id INTEGER NOT NULL,
	storage_id INTEGER NOT NULL,
	location_id INTEGER NOT NULL,
	CONSTRAINT pk_imagestorageplacement PRIMARY KEY (id),
	CONSTRAINT fk_imagestorageplacement_location_id_imagestoragelocation FOREIGN KEY(location_id) REFERENCES imagestoragelocation (id),
	CONSTRAINT fk_imagestorageplacement_storage_id_imagestorage FOREIGN KEY(storage_id) REFERENCES imagestorage (id)
);
INSERT INTO imagestorageplacement VALUES(1,1,9);
INSERT INTO imagestorageplacement VALUES(2,2,9);
CREATE TABLE imagestoragesignature (
	id INTEGER NOT NULL,
	storage_id INTEGER NOT NULL,
	kind_id INTEGER NOT NULL,
	signature TEXT,
	uploading BOOLEAN,
	CONSTRAINT pk_imagestoragesignature PRIMARY KEY (id),
	CONSTRAINT fk_imagestoragesignature_kind_id_imagestoragesignaturekind FOREIGN KEY(kind_id) REFERENCES imagestoragesignaturekind (id),
	CONSTRAINT fk_imagestoragesignature_storage_id_imagestorage FOREIGN KEY(storage_id) REFERENCES imagestorage (id)
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
INSERT INTO label VALUES(1,'7a079b17-8083-4151-829b-d13e0462cf4b','architecture','x86_64',1,1);
INSERT INTO label VALUES(2,'30b3afe7-954d-4cec-959f-4b730aa82719','build-date','2026-07-22T06:49:45Z',1,1);
INSERT INTO label VALUES(3,'fc3602fd-6df0-40be-99f9-79c27d56394b','com.redhat.component','ubi9-micro-container',1,1);
INSERT INTO label VALUES(4,'348a2c75-cc0c-4f89-bedf-fe79b5d3ff35','com.redhat.license_terms','https://www.redhat.com/en/about/red-hat-end-user-license-agreements#UBI',1,1);
INSERT INTO label VALUES(5,'279f2816-75d0-4ba2-ad39-0d91775f1047','cpe','cpe:/a:redhat:enterprise_linux:9::appstream',1,1);
INSERT INTO label VALUES(6,'0abfb8de-2593-40bb-8906-6d369663199a','description','Very small image which doesn''t install the package manager.',1,1);
INSERT INTO label VALUES(7,'8c6311bc-edc0-478f-aea8-3775eb4c80a5','distribution-scope','public',1,1);
INSERT INTO label VALUES(8,'e230ab35-2788-4d51-8637-0c240cecefc0','io.buildah.version','1.44.0',1,1);
INSERT INTO label VALUES(9,'03516feb-e9c9-4b60-9d74-72a3cef16184','io.k8s.description','Very small image which doesn''t install the package manager.',1,1);
INSERT INTO label VALUES(10,'d9556794-5277-4bd6-8d66-b6cf7ac4adec','io.k8s.display-name','Red Hat Universal Base Image 9 Micro',1,1);
INSERT INTO label VALUES(11,'13b1ec0f-9e5e-4b28-ba10-be34634fce7d','io.openshift.expose-services','',1,1);
INSERT INTO label VALUES(12,'ea30116d-f49c-484b-877b-ba1727cb3039','maintainer','Red Hat, Inc.',1,1);
INSERT INTO label VALUES(13,'c981f910-1c0e-4496-bebe-bb1e00570b11','name','ubi9/ubi-micro',1,1);
INSERT INTO label VALUES(14,'e6cec0b9-13d2-468b-840e-8aa7551aed50','org.opencontainers.image.created','2026-07-22T06:49:45Z',1,1);
INSERT INTO label VALUES(15,'095cc9a0-1e96-4fe4-bca2-bc3e17ce98b8','org.opencontainers.image.revision','97262785bdef2694cdc29ef7ef158812c44b97e0',1,1);
INSERT INTO label VALUES(16,'1e76c823-fc01-49b6-9c47-48564d74a53e','release','1784702951',1,1);
INSERT INTO label VALUES(17,'391516f7-9930-40f5-a611-431de97aecc0','summary','ubi9 micro image',1,1);
INSERT INTO label VALUES(18,'c7ba73b4-fec8-4b45-b586-02c01b33b522','url','https://catalog.redhat.com/en/search?searchType=containers',1,1);
INSERT INTO label VALUES(19,'dab671b8-50ac-4e25-a042-466635b5b7c9','vcs-ref','97262785bdef2694cdc29ef7ef158812c44b97e0',1,1);
INSERT INTO label VALUES(20,'def0a706-d778-4973-8508-d41ecd41bd86','vcs-type','git',1,1);
INSERT INTO label VALUES(21,'cf562397-3e95-4a9b-a448-7a72ea15b353','vendor','Red Hat, Inc.',1,1);
INSERT INTO label VALUES(22,'86a286d0-289a-43ae-b019-ce072379602f','version','9.8',1,1);
INSERT INTO label VALUES(23,'f39d3d4a-a1c8-4e3e-bff5-f1f866db6f47','architecture','x86_64',1,1);
INSERT INTO label VALUES(24,'e8d68758-4b71-4f34-aba3-d9ea3813de08','build-date','2026-07-22T06:49:45Z',1,1);
INSERT INTO label VALUES(25,'b1449fdc-0473-4a8c-b1de-eb3ce9793ae0','com.redhat.component','ubi9-micro-container',1,1);
INSERT INTO label VALUES(26,'1e7ca078-afa9-44dc-9432-32841f47b9c6','com.redhat.license_terms','https://www.redhat.com/en/about/red-hat-end-user-license-agreements#UBI',1,1);
INSERT INTO label VALUES(27,'2671ad57-630a-4944-a0b7-98e245a6c69f','cpe','cpe:/a:redhat:enterprise_linux:9::appstream',1,1);
INSERT INTO label VALUES(28,'297cfc37-4bfb-4cb1-b2f8-f92e6ad3e0c2','description','Very small image which doesn''t install the package manager.',1,1);
INSERT INTO label VALUES(29,'e4af2637-1c18-4461-b47b-1a0bf17455c4','distribution-scope','public',1,1);
INSERT INTO label VALUES(30,'9fbc785b-5ea8-46f1-89b5-f7c3993bdb6b','io.buildah.version','1.44.0',1,1);
INSERT INTO label VALUES(31,'dd030bcf-8072-4798-8b4a-46f45b079753','io.k8s.description','Very small image which doesn''t install the package manager.',1,1);
INSERT INTO label VALUES(32,'3bb2bea0-9ce5-494b-b284-d5b42eaafb1f','io.k8s.display-name','Red Hat Universal Base Image 9 Micro',1,1);
INSERT INTO label VALUES(33,'c9c80abc-d2bf-47e6-b8f5-a865eb19b3f7','io.openshift.expose-services','',1,1);
INSERT INTO label VALUES(34,'309b77d3-4e49-4313-85f7-e095d20cd235','maintainer','Red Hat, Inc.',1,1);
INSERT INTO label VALUES(35,'4c89a918-9cf7-4c68-8df0-0f0b87e2120c','name','ubi9/ubi-micro',1,1);
INSERT INTO label VALUES(36,'3a5c1634-bff0-4174-810e-8688db6be999','org.opencontainers.image.created','2026-07-22T06:49:45Z',1,1);
INSERT INTO label VALUES(37,'8b1ddb0b-bfc1-4ca3-a41a-89cfe1f6425e','org.opencontainers.image.revision','97262785bdef2694cdc29ef7ef158812c44b97e0',1,1);
INSERT INTO label VALUES(38,'43b465c1-aa38-4e0a-9f48-e2417a2cbfc0','release','1784702951',1,1);
INSERT INTO label VALUES(39,'2d9e562d-bf4e-4128-a7d7-2d6d574d4717','summary','ubi9 micro image',1,1);
INSERT INTO label VALUES(40,'fe24825c-9cc1-488b-a383-2f522a21f7b3','url','https://catalog.redhat.com/en/search?searchType=containers',1,1);
INSERT INTO label VALUES(41,'e2b22546-1097-4628-9775-02ff9ce3df06','vcs-ref','97262785bdef2694cdc29ef7ef158812c44b97e0',1,1);
INSERT INTO label VALUES(42,'0478a66e-3ece-4cb0-9d05-86fab9eca1b9','vcs-type','git',1,1);
INSERT INTO label VALUES(43,'725428b9-66e3-41c4-9d25-aba754483716','vendor','Red Hat, Inc.',1,1);
INSERT INTO label VALUES(44,'721667ee-3220-4db9-8ab6-e1eeb27605e9','version','9.8',1,1);
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
CREATE TABLE quayrelease (
	id INTEGER NOT NULL,
	service_id INTEGER NOT NULL,
	version VARCHAR(255) NOT NULL,
	region_id INTEGER NOT NULL,
	reverted BOOLEAN NOT NULL,
	created DATETIME NOT NULL,
	CONSTRAINT pk_quayrelease PRIMARY KEY (id),
	CONSTRAINT fk_quayrelease_region_id_quayregion FOREIGN KEY(region_id) REFERENCES quayregion (id),
	CONSTRAINT fk_quayrelease_service_id_quayservice FOREIGN KEY(service_id) REFERENCES quayservice (id)
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
INSERT INTO servicekey VALUES(1,'https://localhost:8443','4Aa9NP_lSNbvHRTs1LD6x5_GQ_85MYisCciOx6wTbHc','quay','{"n": "pM-pneU9dirbaK83RlyBigvrkIsMsVwRFaC7Pd_FJYVnjHGhEv4MjZ63aM9_QJ-XyHAKDZEZqo3S8n08Hy_Zk1znLsQcL3UGZWaS7NfX0RSwzlhiaFWw7Sw3M7bHuQZmKkZ-wRs0fMCaxp6RqNmbZwNNgCNFDkdhiEu3EgWy8MnIyHw6FK_Sdf5a4FredBpxqcSYTVntCvUitLJ2N824fm2NXF8ZJYJmJqQ2YHbjNleimu1nwl1UGuFujwNQ5MT6Spa2nJaO_fiuVYdQzAjHmgB80aPke2Dze0tw7wwV2cpvggY6eoRcc94LMMN62LSkDx8-PsI9fA0XDIo1K4z19Q", "e": "AQAB", "kty": "RSA", "kid": "4Aa9NP_lSNbvHRTs1LD6x5_GQ_85MYisCciOx6wTbHc"}','{"created_by": "CLI tool"}','2026-07-31 12:36:21.589091','2026-07-31 14:36:21.528590',NULL,1);
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
CREATE TABLE userregion (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	location_id INTEGER NOT NULL,
	CONSTRAINT pk_userregion PRIMARY KEY (id),
	CONSTRAINT fk_userregion_location_id_imagestoragelocation FOREIGN KEY(location_id) REFERENCES imagestoragelocation (id),
	CONSTRAINT fk_userregion_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
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
	CONSTRAINT fk_permissionprototype_activating_user_id_user FOREIGN KEY(activating_user_id) REFERENCES user (id),
	CONSTRAINT fk_permissionprototype_delegate_team_id_team FOREIGN KEY(delegate_team_id) REFERENCES team (id),
	CONSTRAINT fk_permissionprototype_delegate_user_id_user FOREIGN KEY(delegate_user_id) REFERENCES user (id),
	CONSTRAINT fk_permissionprototype_org_id_user FOREIGN KEY(org_id) REFERENCES user (id),
	CONSTRAINT fk_permissionprototype_role_id_role FOREIGN KEY(role_id) REFERENCES role (id)
);
CREATE TABLE repositoryactioncount (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	count INTEGER NOT NULL,
	date DATE NOT NULL,
	CONSTRAINT pk_repositoryactioncount PRIMARY KEY (id),
	CONSTRAINT fk_repositoryactioncount_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
INSERT INTO repositoryactioncount VALUES(1,1,0,'2026-07-30');
INSERT INTO repositoryactioncount VALUES(2,2,0,'2026-07-30');
CREATE TABLE repositoryauthorizedemail (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	email VARCHAR(255) NOT NULL,
	code VARCHAR(255) NOT NULL,
	confirmed BOOLEAN NOT NULL,
	CONSTRAINT pk_repositoryauthorizedemail PRIMARY KEY (id),
	CONSTRAINT fk_repositoryauthorizedemail_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE repositorynotification (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	repository_id INTEGER NOT NULL,
	event_id INTEGER NOT NULL,
	method_id INTEGER NOT NULL,
	title VARCHAR(255),
	config_json TEXT NOT NULL,
	event_config_json TEXT NOT NULL, number_of_failures INTEGER DEFAULT '0' NOT NULL, last_ran_ms BIGINT,
	CONSTRAINT pk_repositorynotification PRIMARY KEY (id),
	CONSTRAINT fk_repositorynotification_event_id_externalnotificationevent FOREIGN KEY(event_id) REFERENCES externalnotificationevent (id),
	CONSTRAINT fk_repositorynotification_method_id_externalnotificationmethod FOREIGN KEY(method_id) REFERENCES externalnotificationmethod (id),
	CONSTRAINT fk_repositorynotification_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE repositorypermission (
	id INTEGER NOT NULL,
	team_id INTEGER,
	user_id INTEGER,
	repository_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	CONSTRAINT pk_repositorypermission PRIMARY KEY (id),
	CONSTRAINT fk_repositorypermission_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repositorypermission_role_id_role FOREIGN KEY(role_id) REFERENCES role (id),
	CONSTRAINT fk_repositorypermission_team_id_team FOREIGN KEY(team_id) REFERENCES team (id),
	CONSTRAINT fk_repositorypermission_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);
INSERT INTO repositorypermission VALUES(1,NULL,1,1,1);
INSERT INTO repositorypermission VALUES(2,NULL,1,2,1);
CREATE TABLE star (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	created DATETIME NOT NULL,
	CONSTRAINT pk_star PRIMARY KEY (id),
	CONSTRAINT fk_star_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_star_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE teammember (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	team_id INTEGER NOT NULL,
	CONSTRAINT pk_teammember PRIMARY KEY (id),
	CONSTRAINT fk_teammember_team_id_team FOREIGN KEY(team_id) REFERENCES team (id),
	CONSTRAINT fk_teammember_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE teammemberinvite (
	id INTEGER NOT NULL,
	user_id INTEGER,
	email VARCHAR(255),
	team_id INTEGER NOT NULL,
	inviter_id INTEGER NOT NULL,
	invite_token VARCHAR(255) NOT NULL,
	CONSTRAINT pk_teammemberinvite PRIMARY KEY (id),
	CONSTRAINT fk_teammemberinvite_inviter_id_user FOREIGN KEY(inviter_id) REFERENCES user (id),
	CONSTRAINT fk_teammemberinvite_team_id_team FOREIGN KEY(team_id) REFERENCES team (id),
	CONSTRAINT fk_teammemberinvite_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
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
	logs_archived BOOLEAN DEFAULT (0) NOT NULL,
	queue_id VARCHAR(255),
	CONSTRAINT pk_repositorybuild PRIMARY KEY (id),
	CONSTRAINT fk_repositorybuild_access_token_id_accesstoken FOREIGN KEY(access_token_id) REFERENCES accesstoken (id),
	CONSTRAINT fk_repositorybuild_pull_robot_id_user FOREIGN KEY(pull_robot_id) REFERENCES user (id),
	CONSTRAINT fk_repositorybuild_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repositorybuild_trigger_id_repositorybuildtrigger FOREIGN KEY(trigger_id) REFERENCES repositorybuildtrigger (id)
);
CREATE TABLE userpromptkind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_userpromptkind PRIMARY KEY (id)
);
INSERT INTO userpromptkind VALUES(1,'confirm_username');
INSERT INTO userpromptkind VALUES(2,'enter_name');
INSERT INTO userpromptkind VALUES(3,'enter_company');
CREATE TABLE userprompt (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	kind_id INTEGER NOT NULL,
	CONSTRAINT pk_userprompt PRIMARY KEY (id),
	CONSTRAINT fk_userprompt_kind_id_userpromptkind FOREIGN KEY(kind_id) REFERENCES userpromptkind (id),
	CONSTRAINT fk_userprompt_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE IF NOT EXISTS "messages" (
	id INTEGER NOT NULL,
	content TEXT NOT NULL,
	uuid VARCHAR(36) DEFAULT ('') NOT NULL,
	media_type_id INTEGER DEFAULT '1' NOT NULL,
	severity VARCHAR(255) DEFAULT 'info' NOT NULL,
	CONSTRAINT pk_messages PRIMARY KEY (id),
	CONSTRAINT fk_messages_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
CREATE TABLE repositorykind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_repositorykind PRIMARY KEY (id)
);
INSERT INTO repositorykind VALUES(1,'image');
INSERT INTO repositorykind VALUES(2,'application');
CREATE TABLE IF NOT EXISTS "repository" (
	id INTEGER NOT NULL,
	namespace_user_id INTEGER,
	name VARCHAR(255) NOT NULL,
	visibility_id INTEGER NOT NULL,
	description TEXT,
	badge_token VARCHAR(255) NOT NULL,
	kind_id INTEGER DEFAULT '1' NOT NULL, trust_enabled BOOLEAN DEFAULT (0) NOT NULL, state INTEGER DEFAULT '0' NOT NULL,
	CONSTRAINT pk_repository PRIMARY KEY (id),
	CONSTRAINT fk_repository_visibility_id_visibility FOREIGN KEY(visibility_id) REFERENCES visibility (id),
	CONSTRAINT fk_repository_namespace_user_id_user FOREIGN KEY(namespace_user_id) REFERENCES user (id),
	CONSTRAINT fk_repository_kind_id_repositorykind FOREIGN KEY(kind_id) REFERENCES repositorykind (id)
);
INSERT INTO repository VALUES(1,1,'test-image',2,NULL,'989d65e7-6bad-4a2e-aeee-6e2a9290e704',1,0,0);
INSERT INTO repository VALUES(2,1,'shared',2,NULL,'b75362e4-d34e-41ef-ba08-958e71c0ab76',1,0,0);
CREATE TABLE teamsync (
	id INTEGER NOT NULL,
	team_id INTEGER NOT NULL,
	transaction_id VARCHAR(255) NOT NULL,
	last_updated DATETIME,
	service_id INTEGER NOT NULL,
	config TEXT NOT NULL,
	CONSTRAINT pk_teamsync PRIMARY KEY (id),
	CONSTRAINT fk_teamsync_service_id_loginservice FOREIGN KEY(service_id) REFERENCES loginservice (id),
	CONSTRAINT fk_teamsync_team_id_team FOREIGN KEY(team_id) REFERENCES team (id)
);
CREATE TABLE repositorysearchscore (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	score BIGINT NOT NULL,
	last_updated DATETIME,
	CONSTRAINT pk_repositorysearchscore PRIMARY KEY (id),
	CONSTRAINT fk_repositorysearchscore_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
INSERT INTO repositorysearchscore VALUES(1,1,0,NULL);
INSERT INTO repositorysearchscore VALUES(2,2,0,NULL);
CREATE TABLE IF NOT EXISTS "imagestorage" (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	image_size BIGINT,
	uncompressed_size BIGINT,
	uploading BOOLEAN,
	cas_path BOOLEAN DEFAULT 0 NOT NULL,
	content_checksum VARCHAR(255),
	CONSTRAINT pk_imagestorage PRIMARY KEY (id)
);
INSERT INTO imagestorage VALUES(1,'5f7ef4c5-e89c-4adc-8d26-f2de242229bc',7255415,23591424,1,1,'sha256:e34240319f3ec71fce6b038cdef069885ea714c00b08b8e166ca3f5511eac601');
INSERT INTO imagestorage VALUES(2,'b342ef51-a995-4ffb-b5fd-10ac7119d72a',4877,NULL,1,1,'sha256:e1cc75ec636fa7d9b8f2ac3f833fb00ae8f7ebd19f3c1989396efa91f78735fc');
CREATE TABLE IF NOT EXISTS "blobupload" (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	byte_count BIGINT NOT NULL,
	sha_state TEXT,
	location_id INTEGER NOT NULL,
	storage_metadata TEXT,
	chunk_count INTEGER DEFAULT '0' NOT NULL,
	uncompressed_byte_count BIGINT,
	created DATETIME DEFAULT '2026-07-31 12:36:16' NOT NULL,
	piece_sha_state TEXT,
	piece_hashes TEXT,
	CONSTRAINT pk_blobupload PRIMARY KEY (id),
	CONSTRAINT fk_blobupload_location_id_imagestoragelocation FOREIGN KEY(location_id) REFERENCES imagestoragelocation (id),
	CONSTRAINT fk_blobupload_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
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
CREATE TABLE disablereason (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_disablereason PRIMARY KEY (id)
);
INSERT INTO disablereason VALUES(1,'user_toggled');
INSERT INTO disablereason VALUES(2,'successive_build_failures');
INSERT INTO disablereason VALUES(3,'successive_build_internal_errors');
CREATE TABLE robotaccountmetadata (
	id INTEGER NOT NULL,
	robot_account_id INTEGER NOT NULL,
	description VARCHAR(255) NOT NULL,
	unstructured_json TEXT NOT NULL,
	CONSTRAINT pk_robotaccountmetadata PRIMARY KEY (id),
	CONSTRAINT fk_robotaccountmetadata_robot_account_id_user FOREIGN KEY(robot_account_id) REFERENCES user (id)
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
CREATE TABLE apprblobplacementlocation (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_apprblobplacementlocation PRIMARY KEY (id)
);
INSERT INTO apprblobplacementlocation VALUES(1,'local_eu');
INSERT INTO apprblobplacementlocation VALUES(2,'local_us');
CREATE TABLE apprtagkind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_apprtagkind PRIMARY KEY (id)
);
INSERT INTO apprtagkind VALUES(1,'tag');
INSERT INTO apprtagkind VALUES(2,'release');
INSERT INTO apprtagkind VALUES(3,'channel');
CREATE TABLE apprblob (
	id INTEGER NOT NULL,
	digest VARCHAR(255) NOT NULL,
	media_type_id INTEGER NOT NULL,
	size BIGINT NOT NULL,
	uncompressed_size BIGINT,
	CONSTRAINT pk_apprblob PRIMARY KEY (id),
	CONSTRAINT fk_apprblob_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
CREATE TABLE apprmanifest (
	id INTEGER NOT NULL,
	digest VARCHAR(255) NOT NULL,
	media_type_id INTEGER NOT NULL,
	manifest_json TEXT NOT NULL,
	CONSTRAINT pk_apprmanifest PRIMARY KEY (id),
	CONSTRAINT fk_apprmanifest_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
CREATE TABLE apprmanifestlist (
	id INTEGER NOT NULL,
	digest VARCHAR(255) NOT NULL,
	manifest_list_json TEXT NOT NULL,
	schema_version VARCHAR(255) NOT NULL,
	media_type_id INTEGER NOT NULL,
	CONSTRAINT pk_apprmanifestlist PRIMARY KEY (id),
	CONSTRAINT fk_apprmanifestlist_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
CREATE TABLE apprblobplacement (
	id INTEGER NOT NULL,
	blob_id INTEGER NOT NULL,
	location_id INTEGER NOT NULL,
	CONSTRAINT pk_apprblobplacement PRIMARY KEY (id),
	CONSTRAINT fk_apprblobplacement_blob_id_apprblob FOREIGN KEY(blob_id) REFERENCES apprblob (id),
	CONSTRAINT fk_apprblobplacement_location_id_apprblobplacementlocation FOREIGN KEY(location_id) REFERENCES apprblobplacementlocation (id)
);
CREATE TABLE apprmanifestblob (
	id INTEGER NOT NULL,
	manifest_id INTEGER NOT NULL,
	blob_id INTEGER NOT NULL,
	CONSTRAINT pk_apprmanifestblob PRIMARY KEY (id),
	CONSTRAINT fk_apprmanifestblob_blob_id_apprblob FOREIGN KEY(blob_id) REFERENCES apprblob (id),
	CONSTRAINT fk_apprmanifestblob_manifest_id_apprmanifest FOREIGN KEY(manifest_id) REFERENCES apprmanifest (id)
);
CREATE TABLE apprmanifestlistmanifest (
	id INTEGER NOT NULL,
	manifest_list_id INTEGER NOT NULL,
	manifest_id INTEGER NOT NULL,
	operating_system VARCHAR(255),
	architecture VARCHAR(255),
	platform_json TEXT,
	media_type_id INTEGER NOT NULL,
	CONSTRAINT pk_apprmanifestlistmanifest PRIMARY KEY (id),
	CONSTRAINT fk_apprmanifestlistmanifest_manifest_id_apprmanifest FOREIGN KEY(manifest_id) REFERENCES apprmanifest (id),
	CONSTRAINT fk_apprmanifestlistmanifest_manifest_list_id_apprmanifestlist FOREIGN KEY(manifest_list_id) REFERENCES apprmanifestlist (id),
	CONSTRAINT fk_apprmanifestlistmanifest_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
CREATE TABLE apprtag (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_list_id INTEGER,
	lifetime_start BIGINT NOT NULL,
	lifetime_end BIGINT,
	hidden BOOLEAN NOT NULL,
	reverted BOOLEAN NOT NULL,
	protected BOOLEAN NOT NULL,
	tag_kind_id INTEGER NOT NULL,
	linked_tag_id INTEGER,
	CONSTRAINT pk_apprtag PRIMARY KEY (id),
	CONSTRAINT fk_apprtag_linked_tag_id_apprtag FOREIGN KEY(linked_tag_id) REFERENCES apprtag (id),
	CONSTRAINT fk_apprtag_manifest_list_id_apprmanifestlist FOREIGN KEY(manifest_list_id) REFERENCES apprmanifestlist (id),
	CONSTRAINT fk_apprtag_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_apprtag_tag_kind_id_apprtagkind FOREIGN KEY(tag_kind_id) REFERENCES apprtagkind (id)
);
CREATE TABLE IF NOT EXISTS "logentry" (
	id BIGINT NOT NULL,
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
CREATE TABLE manifestlabel (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_id INTEGER NOT NULL,
	label_id INTEGER NOT NULL,
	CONSTRAINT pk_manifestlabel PRIMARY KEY (id),
	CONSTRAINT fk_manifestlabel_label_id_label FOREIGN KEY(label_id) REFERENCES label (id),
	CONSTRAINT fk_manifestlabel_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id),
	CONSTRAINT fk_manifestlabel_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
INSERT INTO manifestlabel VALUES(1,1,1,1);
INSERT INTO manifestlabel VALUES(2,1,1,2);
INSERT INTO manifestlabel VALUES(3,1,1,3);
INSERT INTO manifestlabel VALUES(4,1,1,4);
INSERT INTO manifestlabel VALUES(5,1,1,5);
INSERT INTO manifestlabel VALUES(6,1,1,6);
INSERT INTO manifestlabel VALUES(7,1,1,7);
INSERT INTO manifestlabel VALUES(8,1,1,8);
INSERT INTO manifestlabel VALUES(9,1,1,9);
INSERT INTO manifestlabel VALUES(10,1,1,10);
INSERT INTO manifestlabel VALUES(11,1,1,11);
INSERT INTO manifestlabel VALUES(12,1,1,12);
INSERT INTO manifestlabel VALUES(13,1,1,13);
INSERT INTO manifestlabel VALUES(14,1,1,14);
INSERT INTO manifestlabel VALUES(15,1,1,15);
INSERT INTO manifestlabel VALUES(16,1,1,16);
INSERT INTO manifestlabel VALUES(17,1,1,17);
INSERT INTO manifestlabel VALUES(18,1,1,18);
INSERT INTO manifestlabel VALUES(19,1,1,19);
INSERT INTO manifestlabel VALUES(20,1,1,20);
INSERT INTO manifestlabel VALUES(21,1,1,21);
INSERT INTO manifestlabel VALUES(22,1,1,22);
INSERT INTO manifestlabel VALUES(23,2,2,23);
INSERT INTO manifestlabel VALUES(24,2,2,24);
INSERT INTO manifestlabel VALUES(25,2,2,25);
INSERT INTO manifestlabel VALUES(26,2,2,26);
INSERT INTO manifestlabel VALUES(27,2,2,27);
INSERT INTO manifestlabel VALUES(28,2,2,28);
INSERT INTO manifestlabel VALUES(29,2,2,29);
INSERT INTO manifestlabel VALUES(30,2,2,30);
INSERT INTO manifestlabel VALUES(31,2,2,31);
INSERT INTO manifestlabel VALUES(32,2,2,32);
INSERT INTO manifestlabel VALUES(33,2,2,33);
INSERT INTO manifestlabel VALUES(34,2,2,34);
INSERT INTO manifestlabel VALUES(35,2,2,35);
INSERT INTO manifestlabel VALUES(36,2,2,36);
INSERT INTO manifestlabel VALUES(37,2,2,37);
INSERT INTO manifestlabel VALUES(38,2,2,38);
INSERT INTO manifestlabel VALUES(39,2,2,39);
INSERT INTO manifestlabel VALUES(40,2,2,40);
INSERT INTO manifestlabel VALUES(41,2,2,41);
INSERT INTO manifestlabel VALUES(42,2,2,42);
INSERT INTO manifestlabel VALUES(43,2,2,43);
INSERT INTO manifestlabel VALUES(44,2,2,44);
CREATE TABLE IF NOT EXISTS "manifestblob" (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_id INTEGER NOT NULL,
	blob_id INTEGER NOT NULL,
	CONSTRAINT pk_manifestblob PRIMARY KEY (id),
	CONSTRAINT fk_manifestblob_blob_id_imagestorage FOREIGN KEY(blob_id) REFERENCES imagestorage (id),
	CONSTRAINT fk_manifestblob_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id),
	CONSTRAINT fk_manifestblob_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
INSERT INTO manifestblob VALUES(1,1,1,1);
INSERT INTO manifestblob VALUES(2,1,1,2);
INSERT INTO manifestblob VALUES(3,2,2,1);
INSERT INTO manifestblob VALUES(4,2,2,2);
CREATE TABLE IF NOT EXISTS "manifest" (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	digest VARCHAR(255) NOT NULL,
	media_type_id INTEGER NOT NULL,
	manifest_bytes TEXT NOT NULL, config_media_type VARCHAR(255), layers_compressed_size BIGINT, subject VARCHAR(255), subject_backfilled BOOLEAN, artifact_type VARCHAR(255), artifact_type_backfilled BOOLEAN,
	CONSTRAINT pk_manifest PRIMARY KEY (id),
	CONSTRAINT fk_manifest_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_manifest_media_type_id_mediatype FOREIGN KEY(media_type_id) REFERENCES mediatype (id)
);
INSERT INTO manifest VALUES(1,1,'sha256:4700df8bfea963e4339efd2990cfe3dc94647417cfdc9db8ffbed024e66cd1a2',16,'{"schemaVersion":2,"mediaType":"application/vnd.docker.distribution.manifest.v2+json","config":{"mediaType":"application/vnd.docker.container.image.v1+json","size":4877,"digest":"sha256:e1cc75ec636fa7d9b8f2ac3f833fb00ae8f7ebd19f3c1989396efa91f78735fc"},"layers":[{"mediaType":"application/vnd.docker.image.rootfs.diff.tar.gzip","size":7255415,"digest":"sha256:e34240319f3ec71fce6b038cdef069885ea714c00b08b8e166ca3f5511eac601"}]}','application/vnd.docker.container.image.v1+json',7255415,NULL,1,NULL,1);
INSERT INTO manifest VALUES(2,2,'sha256:4700df8bfea963e4339efd2990cfe3dc94647417cfdc9db8ffbed024e66cd1a2',16,'{"schemaVersion":2,"mediaType":"application/vnd.docker.distribution.manifest.v2+json","config":{"mediaType":"application/vnd.docker.container.image.v1+json","size":4877,"digest":"sha256:e1cc75ec636fa7d9b8f2ac3f833fb00ae8f7ebd19f3c1989396efa91f78735fc"},"layers":[{"mediaType":"application/vnd.docker.image.rootfs.diff.tar.gzip","size":7255415,"digest":"sha256:e34240319f3ec71fce6b038cdef069885ea714c00b08b8e166ca3f5511eac601"}]}','application/vnd.docker.container.image.v1+json',7255415,NULL,1,NULL,1);
CREATE TABLE tagkind (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_tagkind PRIMARY KEY (id)
);
INSERT INTO tagkind VALUES(1,'tag');
CREATE TABLE manifestchild (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_id INTEGER NOT NULL,
	child_manifest_id INTEGER NOT NULL,
	CONSTRAINT pk_manifestchild PRIMARY KEY (id),
	CONSTRAINT fk_manifestchild_child_manifest_id_manifest FOREIGN KEY(child_manifest_id) REFERENCES manifest (id),
	CONSTRAINT fk_manifestchild_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id),
	CONSTRAINT fk_manifestchild_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE tag (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	repository_id INTEGER NOT NULL,
	manifest_id INTEGER,
	lifetime_start_ms BIGINT NOT NULL,
	lifetime_end_ms BIGINT,
	hidden BOOLEAN DEFAULT (0) NOT NULL,
	reversion BOOLEAN DEFAULT (0) NOT NULL,
	tag_kind_id INTEGER NOT NULL,
	linked_tag_id INTEGER,
	CONSTRAINT pk_tag PRIMARY KEY (id),
	CONSTRAINT fk_tag_linked_tag_id_tag FOREIGN KEY(linked_tag_id) REFERENCES tag (id),
	CONSTRAINT fk_tag_manifest_id_manifest FOREIGN KEY(manifest_id) REFERENCES manifest (id),
	CONSTRAINT fk_tag_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_tag_tag_kind_id_tagkind FOREIGN KEY(tag_kind_id) REFERENCES tagkind (id)
);
INSERT INTO tag VALUES(1,'v1',1,1,1785501535630,NULL,0,0,1,NULL);
INSERT INTO tag VALUES(2,'v1',2,2,1785501536457,NULL,0,0,1,NULL);
INSERT INTO tag VALUES(3,'v2',2,2,1785501537160,NULL,0,0,1,NULL);
CREATE TABLE namespacegeorestriction (
	id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	added DATETIME NOT NULL,
	description VARCHAR(255) NOT NULL,
	unstructured_json TEXT NOT NULL,
	restricted_region_iso_code VARCHAR(255) NOT NULL,
	CONSTRAINT pk_namespacegeorestriction PRIMARY KEY (id),
	CONSTRAINT fk_namespacegeorestriction_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
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
INSERT INTO logentry3 VALUES(1,97,1,1,NULL,'2026-07-31 12:36:43.505203','10.88.0.1','{"kind": "user", "type": "v2auth", "useragent": "containers/5.34.3 (github.com/containers/image)"}');
INSERT INTO logentry3 VALUES(2,42,1,1,1,'2026-07-31 12:38:55.634559','10.88.0.1','{"repo": "test-image", "namespace": "init", "user-agent": "containers/5.34.3 (github.com/containers/image)", "tag": "v1", "username": "init", "resolved_ip": {"provider": "internet", "service": null, "sync_token": "1645662201", "country_iso_code": null, "aws_region": null, "continent": null}}');
INSERT INTO logentry3 VALUES(3,42,1,1,2,'2026-07-31 12:38:56.460268','10.88.0.1','{"repo": "shared", "namespace": "init", "user-agent": "containers/5.34.3 (github.com/containers/image)", "tag": "v1", "username": "init", "resolved_ip": {"provider": "internet", "service": null, "sync_token": "1645662201", "country_iso_code": null, "aws_region": null, "continent": null}}');
INSERT INTO logentry3 VALUES(4,42,1,1,2,'2026-07-31 12:38:57.166389','10.88.0.1','{"repo": "shared", "namespace": "init", "user-agent": "containers/5.34.3 (github.com/containers/image)", "tag": "v2", "username": "init", "resolved_ip": {"provider": "internet", "service": null, "sync_token": "1645662201", "country_iso_code": null, "aws_region": null, "continent": null}}');
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
	CONSTRAINT fk_repomirrorrule_left_child_id_repomirrorrule FOREIGN KEY(left_child_id) REFERENCES repomirrorrule (id),
	CONSTRAINT fk_repomirrorrule_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repomirrorrule_right_child_id_repomirrorrule FOREIGN KEY(right_child_id) REFERENCES repomirrorrule (id)
);
CREATE TABLE robotaccounttoken (
	id INTEGER NOT NULL,
	robot_account_id INTEGER NOT NULL,
	token VARCHAR(255) NOT NULL,
	fully_migrated BOOLEAN DEFAULT '0' NOT NULL,
	CONSTRAINT pk_robotaccounttoken PRIMARY KEY (id),
	CONSTRAINT fk_robotaccounttoken_robot_account_id_user FOREIGN KEY(robot_account_id) REFERENCES user (id)
);
CREATE TABLE IF NOT EXISTS "accesstoken" (
	id INTEGER NOT NULL,
	friendly_name VARCHAR(255),
	repository_id INTEGER NOT NULL,
	created DATETIME NOT NULL,
	role_id INTEGER NOT NULL,
	"temporary" BOOLEAN NOT NULL,
	kind_id INTEGER,
	token_code VARCHAR(255) NOT NULL,
	token_name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_accesstoken PRIMARY KEY (id),
	CONSTRAINT fk_accesstoken_kind_id_accesstokenkind FOREIGN KEY(kind_id) REFERENCES accesstokenkind (id),
	CONSTRAINT fk_accesstoken_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_accesstoken_role_id_role FOREIGN KEY(role_id) REFERENCES role (id)
);
CREATE TABLE IF NOT EXISTS "appspecificauthtoken" (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	created DATETIME NOT NULL,
	expiration DATETIME,
	last_accessed DATETIME,
	token_name VARCHAR(255) NOT NULL,
	token_secret VARCHAR(255) NOT NULL,
	CONSTRAINT pk_appspecificauthtoken PRIMARY KEY (id),
	CONSTRAINT fk_appspecificauthtoken_user_id_user FOREIGN KEY(user_id) REFERENCES user (id)
);
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
	CONSTRAINT fk_oauthaccesstoken_authorized_user_id_user FOREIGN KEY(authorized_user_id) REFERENCES user (id),
	CONSTRAINT fk_oauthaccesstoken_application_id_oauthapplication FOREIGN KEY(application_id) REFERENCES oauthapplication (id)
);
INSERT INTO oauthaccesstoken VALUES(1,'f271481d-5929-4bb0-9a57-aa5bfd35df85',1,1,'org:admin repo:admin repo:create repo:read repo:write super:user user:admin user:read','token','2026-07-31 15:06:42.569941','','FIXTURE-REDACTED-OAUTH-TOKEN','FIXTURE-REDACTED');
CREATE TABLE IF NOT EXISTS "oauthapplication" (
	id INTEGER NOT NULL,
	client_id VARCHAR(255) NOT NULL,
	redirect_uri VARCHAR(255) NOT NULL,
	application_uri VARCHAR(255) NOT NULL,
	organization_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	description TEXT NOT NULL,
	gravatar_email VARCHAR(255),
	secure_client_secret VARCHAR(255),
	fully_migrated BOOLEAN DEFAULT '0' NOT NULL,
	CONSTRAINT pk_oauthapplication PRIMARY KEY (id),
	CONSTRAINT fk_oauthapplication_organization_id_user FOREIGN KEY(organization_id) REFERENCES user (id)
);
INSERT INTO oauthapplication VALUES(1,'init','','',1,'automation','Application token generated via /api/v1/user/initialize',NULL,'FIXTURE-REDACTED-CLIENT-SECRET',0);
CREATE TABLE IF NOT EXISTS "oauthauthorizationcode" (
	id INTEGER NOT NULL,
	application_id INTEGER NOT NULL,
	scope VARCHAR(255) NOT NULL,
	data TEXT NOT NULL,
	code_credential VARCHAR(255) NOT NULL,
	code_name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_oauthauthorizationcode PRIMARY KEY (id),
	CONSTRAINT fk_oauthauthorizationcode_application_id_oauthapplication FOREIGN KEY(application_id) REFERENCES oauthapplication (id)
);
CREATE TABLE IF NOT EXISTS "repositorybuildtrigger" (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	service_id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	connected_user_id INTEGER NOT NULL,
	config TEXT NOT NULL,
	write_token_id INTEGER,
	pull_robot_id INTEGER,
	disabled_reason_id INTEGER,
	enabled BOOLEAN DEFAULT 1 NOT NULL,
	successive_failure_count INTEGER DEFAULT '0' NOT NULL,
	successive_internal_error_count INTEGER DEFAULT '0' NOT NULL,
	disabled_datetime DATETIME,
	secure_auth_token VARCHAR(255),
	secure_private_key TEXT,
	fully_migrated BOOLEAN DEFAULT '0' NOT NULL,
	CONSTRAINT pk_repositorybuildtrigger PRIMARY KEY (id),
	CONSTRAINT fk_repositorybuildtrigger_service_id_buildtriggerservice FOREIGN KEY(service_id) REFERENCES buildtriggerservice (id),
	CONSTRAINT fk_repositorybuildtrigger_disabled_reason_id_disablereason FOREIGN KEY(disabled_reason_id) REFERENCES disablereason (id),
	CONSTRAINT fk_repositorybuildtrigger_connected_user_id_user FOREIGN KEY(connected_user_id) REFERENCES user (id),
	CONSTRAINT fk_repositorybuildtrigger_pull_robot_id_user FOREIGN KEY(pull_robot_id) REFERENCES user (id),
	CONSTRAINT fk_repositorybuildtrigger_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repositorybuildtrigger_write_token_id_accesstoken FOREIGN KEY(write_token_id) REFERENCES accesstoken (id)
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
CREATE TABLE uploadedblob (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	blob_id INTEGER NOT NULL,
	uploaded_at DATETIME NOT NULL,
	expires_at DATETIME NOT NULL,
	CONSTRAINT pk_uploadedblob PRIMARY KEY (id),
	CONSTRAINT fk_uploadedblob_blob_id_imagestorage FOREIGN KEY(blob_id) REFERENCES imagestorage (id),
	CONSTRAINT fk_uploadedblob_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
INSERT INTO uploadedblob VALUES(1,1,1,'2026-07-31 12:38:55.477019','2026-07-31 13:38:55.477003');
INSERT INTO uploadedblob VALUES(2,1,2,'2026-07-31 12:38:55.575652','2026-07-31 13:38:55.575635');
INSERT INTO uploadedblob VALUES(3,2,1,'2026-07-31 12:38:56.327330','2026-07-31 13:38:56.327317');
INSERT INTO uploadedblob VALUES(4,2,2,'2026-07-31 12:38:56.404546','2026-07-31 13:38:56.404529');
CREATE TABLE userorganizationquota (
	id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	limit_bytes BIGINT NOT NULL,
	CONSTRAINT pk_userorganizationquota PRIMARY KEY (id),
	CONSTRAINT fk_userorganizationquota_organization FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE quotatype (
	id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	CONSTRAINT pk_quotatype PRIMARY KEY (id)
);
INSERT INTO quotatype VALUES(1,'Warning');
INSERT INTO quotatype VALUES(2,'Reject');
CREATE TABLE quotalimits (
	id INTEGER NOT NULL,
	quota_id INTEGER NOT NULL,
	quota_type_id INTEGER NOT NULL,
	percent_of_limit INTEGER NOT NULL,
	CONSTRAINT pk_quotalimits PRIMARY KEY (id),
	CONSTRAINT fk_quotalimit_type FOREIGN KEY(quota_type_id) REFERENCES quotatype (id),
	CONSTRAINT fk_quotalimit_id FOREIGN KEY(quota_id) REFERENCES userorganizationquota (id)
);
CREATE TABLE IF NOT EXISTS "proxycacheconfig" (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	creation_date DATETIME NOT NULL,
	upstream_registry VARCHAR(2048) NOT NULL,
	upstream_registry_username VARCHAR(4096),
	upstream_registry_password VARCHAR(4096),
	expiration_s INTEGER DEFAULT '86400',
	insecure BOOLEAN DEFAULT 0 NOT NULL,
	CONSTRAINT pk_proxy_cache_config PRIMARY KEY (id),
	CONSTRAINT fk_proxy_cache_config_organization_id FOREIGN KEY(organization_id) REFERENCES user (id)
);
CREATE TABLE IF NOT EXISTS "repomirrorconfig" (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	creation_date DATETIME NOT NULL,
	is_enabled BOOLEAN NOT NULL,
	mirror_type INTEGER NOT NULL,
	internal_robot_id INTEGER NOT NULL,
	external_registry_username VARCHAR(4096),
	external_registry_password VARCHAR(4096),
	external_registry_config TEXT NOT NULL,
	sync_interval INTEGER DEFAULT '60' NOT NULL,
	sync_start_date DATETIME,
	sync_expiration_date DATETIME,
	sync_retries_remaining INTEGER DEFAULT '3' NOT NULL,
	sync_status INTEGER NOT NULL,
	sync_transaction_id VARCHAR(36),
	root_rule_id INTEGER NOT NULL,
	external_reference TEXT NOT NULL,
	CONSTRAINT pk_repomirrorconfig PRIMARY KEY (id),
	CONSTRAINT fk_repomirrorconfig_internal_robot_id_user FOREIGN KEY(internal_robot_id) REFERENCES user (id),
	CONSTRAINT fk_repomirrorconfig_root_rule_id_repomirrorrule FOREIGN KEY(root_rule_id) REFERENCES repomirrorrule (id),
	CONSTRAINT fk_repomirrorconfig_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE quotanamespacesize (
	id INTEGER NOT NULL,
	namespace_user_id INTEGER NOT NULL,
	size_bytes BIGINT DEFAULT '0' NOT NULL,
	backfill_start_ms BIGINT,
	backfill_complete BOOLEAN DEFAULT (0) NOT NULL,
	CONSTRAINT pk_quotanamespacesizeid PRIMARY KEY (id),
	CONSTRAINT fk_quotanamespacesize_namespace_user_id_user FOREIGN KEY(namespace_user_id) REFERENCES user (id)
);
CREATE TABLE quotarepositorysize (
	id INTEGER NOT NULL,
	repository_id INTEGER NOT NULL,
	size_bytes BIGINT DEFAULT '0' NOT NULL,
	backfill_start_ms BIGINT,
	backfill_complete BOOLEAN DEFAULT (0) NOT NULL,
	CONSTRAINT pk_quotarepositorysizeid PRIMARY KEY (id),
	CONSTRAINT fk_quotarepositorysize_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id)
);
CREATE TABLE redhatsubscriptions (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	account_number INTEGER NOT NULL,
	CONSTRAINT pk_redhatsubscriptions PRIMARY KEY (id),
	CONSTRAINT fk_redhatsubscriptions FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE quotaregistrysize (
	id INTEGER NOT NULL,
	size_bytes BIGINT DEFAULT '0' NOT NULL,
	running BOOLEAN DEFAULT (0) NOT NULL,
	queued BOOLEAN DEFAULT (0) NOT NULL,
	completed_ms BIGINT,
	CONSTRAINT pk_quotaregistrysizeid PRIMARY KEY (id)
);
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
INSERT INTO user VALUES(1,'c6f515bd-b3fa-4c00-9e50-699d713a7ea5','init','FIXTURE-NOT-A-REAL-HASH','init@quay.io',1,NULL,0,0,0,0,'2026-07-31 12:36:42.332282',1209600,1,NULL,NULL,NULL,NULL,NULL,NULL,'2026-07-31 12:36:42.332287',NULL);
CREATE TABLE organizationrhskus (
	id INTEGER NOT NULL,
	subscription_id INTEGER NOT NULL,
	org_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL, quantity INTEGER,
	CONSTRAINT pk_organizationrhskus PRIMARY KEY (id),
	CONSTRAINT fk_organizationrhskus_userid FOREIGN KEY(user_id) REFERENCES user (id),
	CONSTRAINT fk_organizationrhskus_orgid FOREIGN KEY(org_id) REFERENCES user (id)
);
CREATE TABLE namespaceautoprunepolicy (
	id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	CONSTRAINT pk_namespaceautoprunepolicyid PRIMARY KEY (id),
	CONSTRAINT fk_namespaceautoprunepolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE autoprunetaskstatus (
	id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	last_ran_ms BIGINT,
	status TEXT,
	CONSTRAINT pk_autoprunetaskstatusid PRIMARY KEY (id),
	CONSTRAINT fk_autoprunetaskstatus_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE IF NOT EXISTS "repositoryautoprunepolicy" (
	id INTEGER NOT NULL,
	uuid VARCHAR(36) NOT NULL,
	repository_id INTEGER NOT NULL,
	namespace_id INTEGER NOT NULL,
	policy TEXT NOT NULL,
	CONSTRAINT pk_repositoryautoprunepolicyid PRIMARY KEY (id),
	CONSTRAINT fk_repositoryautoprunepolicy_repository_id_repository FOREIGN KEY(repository_id) REFERENCES repository (id),
	CONSTRAINT fk_repositoryautoprunepolicy_namespace_id_user FOREIGN KEY(namespace_id) REFERENCES user (id)
);
CREATE TABLE oauthassignedtoken (
	id INTEGER NOT NULL,
	uuid VARCHAR(255) NOT NULL,
	assigned_user_id INTEGER NOT NULL,
	application_id INTEGER NOT NULL,
	redirect_uri VARCHAR(255),
	scope VARCHAR(255) NOT NULL,
	response_type VARCHAR(255),
	CONSTRAINT pk_oauthassignedtoken PRIMARY KEY (id),
	CONSTRAINT fk_oauthassignedtoken_application_oauthapplication FOREIGN KEY(application_id) REFERENCES oauthapplication (id),
	CONSTRAINT fk_oauthassignedtoken_assigned_user_user FOREIGN KEY(assigned_user_id) REFERENCES user (id)
);
CREATE TABLE tagnotificationsuccess (
	id INTEGER NOT NULL,
	notification_id INTEGER NOT NULL,
	tag_id INTEGER NOT NULL,
	method_id INTEGER NOT NULL,
	CONSTRAINT pk_tag_notification_success PRIMARY KEY (id),
	CONSTRAINT fk_tag_notification_success_notification_id FOREIGN KEY(notification_id) REFERENCES repositorynotification (id),
	CONSTRAINT fk_tag_notification_success_tag_id FOREIGN KEY(tag_id) REFERENCES tag (id),
	CONSTRAINT fk_tag_notification_success_method_id FOREIGN KEY(method_id) REFERENCES externalnotificationmethod (id)
);
CREATE UNIQUE INDEX accesstokenkind_name ON accesstokenkind (name);
CREATE UNIQUE INDEX buildtriggerservice_name ON buildtriggerservice (name);
CREATE UNIQUE INDEX externalnotificationevent_name ON externalnotificationevent (name);
CREATE UNIQUE INDEX externalnotificationmethod_name ON externalnotificationmethod (name);
CREATE UNIQUE INDEX imagestoragelocation_name ON imagestoragelocation (name);
CREATE UNIQUE INDEX imagestoragesignaturekind_name ON imagestoragesignaturekind (name);
CREATE UNIQUE INDEX imagestoragetransformation_name ON imagestoragetransformation (name);
CREATE UNIQUE INDEX labelsourcetype_name ON labelsourcetype (name);
CREATE UNIQUE INDEX logentrykind_name ON logentrykind (name);
CREATE UNIQUE INDEX loginservice_name ON loginservice (name);
CREATE UNIQUE INDEX mediatype_name ON mediatype (name);
CREATE UNIQUE INDEX notificationkind_name ON notificationkind (name);
CREATE UNIQUE INDEX quayregion_name ON quayregion (name);
CREATE UNIQUE INDEX quayservice_name ON quayservice (name);
CREATE INDEX queueitem_queue_name ON queueitem (queue_name);
CREATE UNIQUE INDEX role_name ON role (name);
CREATE INDEX servicekeyapproval_approval_type ON servicekeyapproval (approval_type);
CREATE INDEX servicekeyapproval_approver_id ON servicekeyapproval (approver_id);
CREATE INDEX teamrole_name ON teamrole (name);
CREATE UNIQUE INDEX visibility_name ON visibility (name);
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
CREATE INDEX notification_created ON notification (created);
CREATE INDEX notification_kind_id ON notification (kind_id);
CREATE INDEX notification_lookup_path ON notification (lookup_path);
CREATE INDEX notification_target_id ON notification (target_id);
CREATE INDEX notification_uuid ON notification (uuid);
CREATE INDEX quayrelease_created ON quayrelease (created);
CREATE INDEX quayrelease_region_id ON quayrelease (region_id);
CREATE INDEX quayrelease_service_id ON quayrelease (service_id);
CREATE INDEX quayrelease_service_id_region_id_created ON quayrelease (service_id, region_id, created);
CREATE UNIQUE INDEX quayrelease_service_id_version_region_id ON quayrelease (service_id, version, region_id);
CREATE INDEX servicekey_approval_id ON servicekey (approval_id);
CREATE UNIQUE INDEX servicekey_kid ON servicekey (kid);
CREATE INDEX servicekey_service ON servicekey (service);
CREATE INDEX team_name ON team (name);
CREATE UNIQUE INDEX team_name_organization_id ON team (name, organization_id);
CREATE INDEX team_organization_id ON team (organization_id);
CREATE INDEX team_role_id ON team (role_id);
CREATE INDEX userregion_location_id ON userregion (location_id);
CREATE INDEX userregion_user_id ON userregion (user_id);
CREATE INDEX permissionprototype_activating_user_id ON permissionprototype (activating_user_id);
CREATE INDEX permissionprototype_delegate_team_id ON permissionprototype (delegate_team_id);
CREATE INDEX permissionprototype_delegate_user_id ON permissionprototype (delegate_user_id);
CREATE INDEX permissionprototype_org_id ON permissionprototype (org_id);
CREATE INDEX permissionprototype_org_id_activating_user_id ON permissionprototype (org_id, activating_user_id);
CREATE INDEX permissionprototype_role_id ON permissionprototype (role_id);
CREATE INDEX repositoryactioncount_date ON repositoryactioncount (date);
CREATE INDEX repositoryactioncount_repository_id ON repositoryactioncount (repository_id);
CREATE UNIQUE INDEX repositoryactioncount_repository_id_date ON repositoryactioncount (repository_id, date);
CREATE UNIQUE INDEX repositoryauthorizedemail_code ON repositoryauthorizedemail (code);
CREATE UNIQUE INDEX repositoryauthorizedemail_email_repository_id ON repositoryauthorizedemail (email, repository_id);
CREATE INDEX repositoryauthorizedemail_repository_id ON repositoryauthorizedemail (repository_id);
CREATE INDEX repositorynotification_event_id ON repositorynotification (event_id);
CREATE INDEX repositorynotification_method_id ON repositorynotification (method_id);
CREATE INDEX repositorynotification_repository_id ON repositorynotification (repository_id);
CREATE INDEX repositorynotification_uuid ON repositorynotification (uuid);
CREATE INDEX repositorypermission_repository_id ON repositorypermission (repository_id);
CREATE INDEX repositorypermission_role_id ON repositorypermission (role_id);
CREATE INDEX repositorypermission_team_id ON repositorypermission (team_id);
CREATE UNIQUE INDEX repositorypermission_team_id_repository_id ON repositorypermission (team_id, repository_id);
CREATE INDEX repositorypermission_user_id ON repositorypermission (user_id);
CREATE UNIQUE INDEX repositorypermission_user_id_repository_id ON repositorypermission (user_id, repository_id);
CREATE INDEX star_repository_id ON star (repository_id);
CREATE INDEX star_user_id ON star (user_id);
CREATE UNIQUE INDEX star_user_id_repository_id ON star (user_id, repository_id);
CREATE INDEX teammember_team_id ON teammember (team_id);
CREATE INDEX teammember_user_id ON teammember (user_id);
CREATE UNIQUE INDEX teammember_user_id_team_id ON teammember (user_id, team_id);
CREATE INDEX teammemberinvite_inviter_id ON teammemberinvite (inviter_id);
CREATE INDEX teammemberinvite_team_id ON teammemberinvite (team_id);
CREATE INDEX teammemberinvite_user_id ON teammemberinvite (user_id);
CREATE INDEX repositorybuild_access_token_id ON repositorybuild (access_token_id);
CREATE INDEX repositorybuild_pull_robot_id ON repositorybuild (pull_robot_id);
CREATE INDEX repositorybuild_queue_id ON repositorybuild (queue_id);
CREATE INDEX repositorybuild_repository_id ON repositorybuild (repository_id);
CREATE INDEX repositorybuild_repository_id_started_phase ON repositorybuild (repository_id, started, phase);
CREATE INDEX repositorybuild_resource_key ON repositorybuild (resource_key);
CREATE INDEX repositorybuild_started ON repositorybuild (started);
CREATE INDEX repositorybuild_started_logs_archived_phase ON repositorybuild (started, logs_archived, phase);
CREATE INDEX repositorybuild_trigger_id ON repositorybuild (trigger_id);
CREATE INDEX repositorybuild_uuid ON repositorybuild (uuid);
CREATE INDEX userpromptkind_name ON userpromptkind (name);
CREATE INDEX userprompt_kind_id ON userprompt (kind_id);
CREATE INDEX userprompt_user_id ON userprompt (user_id);
CREATE UNIQUE INDEX userprompt_user_id_kind_id ON userprompt (user_id, kind_id);
CREATE INDEX queueitem_processing_expires_available ON queueitem (processing_expires, available);
CREATE INDEX queueitem_pe_aafter_qname_rremaining_available ON queueitem (processing_expires, available_after, queue_name, retries_remaining, available);
CREATE INDEX queueitem_pexpires_aafter_rremaining_available ON queueitem (processing_expires, available_after, retries_remaining, available);
CREATE INDEX queueitem_processing_expires_queue_name_available ON queueitem (processing_expires, queue_name, available);
CREATE INDEX messages_uuid ON messages (uuid);
CREATE INDEX messages_media_type_id ON messages (media_type_id);
CREATE INDEX messages_severity ON messages (severity);
CREATE UNIQUE INDEX queueitem_state_id ON queueitem (state_id);
CREATE UNIQUE INDEX repositorykind_name ON repositorykind (name);
CREATE INDEX repository_namespace_user_id ON repository (namespace_user_id);
CREATE INDEX repository_visibility_id ON repository (visibility_id);
CREATE INDEX repository_description__fulltext ON repository (description);
CREATE UNIQUE INDEX repository_namespace_user_id_name ON repository (namespace_user_id, name);
CREATE INDEX repository_name__fulltext ON repository (name);
CREATE INDEX repository_kind_id ON repository (kind_id);
CREATE INDEX teamsync_last_updated ON teamsync (last_updated);
CREATE INDEX teamsync_service_id ON teamsync (service_id);
CREATE UNIQUE INDEX teamsync_team_id ON teamsync (team_id);
CREATE UNIQUE INDEX repositorysearchscore_repository_id ON repositorysearchscore (repository_id);
CREATE INDEX repositorysearchscore_score ON repositorysearchscore (score);
CREATE INDEX imagestorage_content_checksum ON imagestorage (content_checksum);
CREATE UNIQUE INDEX imagestorage_uuid ON imagestorage (uuid);
CREATE UNIQUE INDEX blobupload_repository_id_uuid ON blobupload (repository_id, uuid);
CREATE INDEX blobupload_repository_id ON blobupload (repository_id);
CREATE INDEX blobupload_location_id ON blobupload (location_id);
CREATE UNIQUE INDEX blobupload_uuid ON blobupload (uuid);
CREATE INDEX blobupload_created ON blobupload (created);
CREATE UNIQUE INDEX deletednamespace_namespace_id ON deletednamespace (namespace_id);
CREATE INDEX deletednamespace_original_email ON deletednamespace (original_email);
CREATE INDEX deletednamespace_original_username ON deletednamespace (original_username);
CREATE INDEX deletednamespace_queue_id ON deletednamespace (queue_id);
CREATE UNIQUE INDEX disablereason_name ON disablereason (name);
CREATE UNIQUE INDEX robotaccountmetadata_robot_account_id ON robotaccountmetadata (robot_account_id);
CREATE INDEX logentry2_account_id ON logentry2 (account_id);
CREATE INDEX logentry2_account_id_datetime ON logentry2 (account_id, datetime);
CREATE INDEX logentry2_datetime ON logentry2 (datetime);
CREATE INDEX logentry2_kind_id ON logentry2 (kind_id);
CREATE INDEX logentry2_performer_id ON logentry2 (performer_id);
CREATE INDEX logentry2_performer_id_datetime ON logentry2 (performer_id, datetime);
CREATE INDEX logentry2_repository_id ON logentry2 (repository_id);
CREATE INDEX logentry2_repository_id_datetime ON logentry2 (repository_id, datetime);
CREATE INDEX logentry2_repository_id_datetime_kind_id ON logentry2 (repository_id, datetime, kind_id);
CREATE UNIQUE INDEX apprblobplacementlocation_name ON apprblobplacementlocation (name);
CREATE UNIQUE INDEX apprtagkind_name ON apprtagkind (name);
CREATE UNIQUE INDEX apprblob_digest ON apprblob (digest);
CREATE INDEX apprblob_media_type_id ON apprblob (media_type_id);
CREATE UNIQUE INDEX apprmanifest_digest ON apprmanifest (digest);
CREATE INDEX apprmanifest_media_type_id ON apprmanifest (media_type_id);
CREATE UNIQUE INDEX apprmanifestlist_digest ON apprmanifestlist (digest);
CREATE INDEX apprmanifestlist_media_type_id ON apprmanifestlist (media_type_id);
CREATE INDEX apprblobplacement_blob_id ON apprblobplacement (blob_id);
CREATE UNIQUE INDEX apprblobplacement_blob_id_location_id ON apprblobplacement (blob_id, location_id);
CREATE INDEX apprblobplacement_location_id ON apprblobplacement (location_id);
CREATE INDEX apprmanifestblob_blob_id ON apprmanifestblob (blob_id);
CREATE INDEX apprmanifestblob_manifest_id ON apprmanifestblob (manifest_id);
CREATE UNIQUE INDEX apprmanifestblob_manifest_id_blob_id ON apprmanifestblob (manifest_id, blob_id);
CREATE INDEX apprmanifestlistmanifest_manifest_id ON apprmanifestlistmanifest (manifest_id);
CREATE INDEX apprmanifestlistmanifest_manifest_list_id ON apprmanifestlistmanifest (manifest_list_id);
CREATE INDEX apprmanifestlistmanifest_manifest_list_id_media_type_id ON apprmanifestlistmanifest (manifest_list_id, media_type_id);
CREATE INDEX apprmanifestlistmanifest_manifest_list_id_operating_system_arch ON apprmanifestlistmanifest (manifest_list_id, operating_system, architecture, media_type_id);
CREATE INDEX apprmanifestlistmanifest_media_type_id ON apprmanifestlistmanifest (media_type_id);
CREATE INDEX apprtag_lifetime_end ON apprtag (lifetime_end);
CREATE INDEX apprtag_linked_tag_id ON apprtag (linked_tag_id);
CREATE INDEX apprtag_manifest_list_id ON apprtag (manifest_list_id);
CREATE INDEX apprtag_repository_id ON apprtag (repository_id);
CREATE INDEX apprtag_repository_id_name ON apprtag (repository_id, name);
CREATE INDEX apprtag_repository_id_name_hidden ON apprtag (repository_id, name, hidden);
CREATE UNIQUE INDEX apprtag_repository_id_name_lifetime_end ON apprtag (repository_id, name, lifetime_end);
CREATE INDEX apprtag_tag_kind_id ON apprtag (tag_kind_id);
CREATE INDEX logentry_account_id ON logentry (account_id);
CREATE INDEX logentry_kind_id ON logentry (kind_id);
CREATE INDEX logentry_repository_id ON logentry (repository_id);
CREATE INDEX logentry_account_id_datetime ON logentry (account_id, datetime);
CREATE INDEX logentry_performer_id ON logentry (performer_id);
CREATE INDEX logentry_repository_id_datetime_kind_id ON logentry (repository_id, datetime, kind_id);
CREATE INDEX logentry_repository_id_datetime ON logentry (repository_id, datetime);
CREATE INDEX logentry_datetime ON logentry (datetime);
CREATE INDEX logentry_performer_id_datetime ON logentry (performer_id, datetime);
CREATE INDEX manifestlabel_label_id ON manifestlabel (label_id);
CREATE INDEX manifestlabel_manifest_id ON manifestlabel (manifest_id);
CREATE UNIQUE INDEX manifestlabel_manifest_id_label_id ON manifestlabel (manifest_id, label_id);
CREATE INDEX manifestlabel_repository_id ON manifestlabel (repository_id);
CREATE INDEX manifestblob_repository_id ON manifestblob (repository_id);
CREATE INDEX manifestblob_blob_id ON manifestblob (blob_id);
CREATE INDEX manifestblob_manifest_id ON manifestblob (manifest_id);
CREATE UNIQUE INDEX manifestblob_manifest_id_blob_id ON manifestblob (manifest_id, blob_id);
CREATE INDEX manifest_repository_id_media_type_id ON manifest (repository_id, media_type_id);
CREATE INDEX manifest_repository_id ON manifest (repository_id);
CREATE INDEX manifest_digest ON manifest (digest);
CREATE INDEX manifest_media_type_id ON manifest (media_type_id);
CREATE UNIQUE INDEX manifest_repository_id_digest ON manifest (repository_id, digest);
CREATE UNIQUE INDEX tagkind_name ON tagkind (name);
CREATE INDEX manifestchild_child_manifest_id ON manifestchild (child_manifest_id);
CREATE INDEX manifestchild_manifest_id ON manifestchild (manifest_id);
CREATE UNIQUE INDEX manifestchild_manifest_id_child_manifest_id ON manifestchild (manifest_id, child_manifest_id);
CREATE INDEX manifestchild_repository_id ON manifestchild (repository_id);
CREATE INDEX manifestchild_repository_id_child_manifest_id ON manifestchild (repository_id, child_manifest_id);
CREATE INDEX manifestchild_repository_id_manifest_id ON manifestchild (repository_id, manifest_id);
CREATE INDEX manifestchild_repository_id_manifest_id_child_manifest_id ON manifestchild (repository_id, manifest_id, child_manifest_id);
CREATE INDEX tag_lifetime_end_ms ON tag (lifetime_end_ms);
CREATE INDEX tag_linked_tag_id ON tag (linked_tag_id);
CREATE INDEX tag_manifest_id ON tag (manifest_id);
CREATE INDEX tag_repository_id ON tag (repository_id);
CREATE INDEX tag_repository_id_name ON tag (repository_id, name);
CREATE INDEX tag_repository_id_name_hidden ON tag (repository_id, name, hidden);
CREATE UNIQUE INDEX tag_repository_id_name_lifetime_end_ms ON tag (repository_id, name, lifetime_end_ms);
CREATE INDEX tag_repository_id_name_tag_kind_id ON tag (repository_id, name, tag_kind_id);
CREATE INDEX tag_tag_kind_id ON tag (tag_kind_id);
CREATE INDEX namespacegeorestriction_namespace_id ON namespacegeorestriction (namespace_id);
CREATE UNIQUE INDEX namespacegeorestriction_namespace_id_restricted_region_iso_code ON namespacegeorestriction (namespace_id, restricted_region_iso_code);
CREATE INDEX namespacegeorestriction_restricted_region_iso_code ON namespacegeorestriction (restricted_region_iso_code);
CREATE INDEX logentry3_account_id_datetime ON logentry3 (account_id, datetime);
CREATE INDEX logentry3_datetime ON logentry3 (datetime);
CREATE INDEX logentry3_performer_id_datetime ON logentry3 (performer_id, datetime);
CREATE INDEX logentry3_repository_id_datetime_kind_id ON logentry3 (repository_id, datetime, kind_id);
CREATE INDEX permissionprototype_uuid ON permissionprototype (uuid);
CREATE INDEX tag_repository_id_lifetime_end_ms ON tag (repository_id, lifetime_end_ms);
CREATE INDEX tag_repository_id_lifetime_start_ms ON tag (repository_id, lifetime_start_ms);
CREATE INDEX repositorybuild_logs_archived ON repositorybuild (logs_archived);
CREATE INDEX repomirrorrule_left_child_id ON repomirrorrule (left_child_id);
CREATE INDEX repomirrorrule_repository_id ON repomirrorrule (repository_id);
CREATE INDEX repomirrorrule_right_child_id ON repomirrorrule (right_child_id);
CREATE INDEX repomirrorrule_rule_type ON repomirrorrule (rule_type);
CREATE UNIQUE INDEX repomirrorrule_uuid ON repomirrorrule (uuid);
CREATE INDEX repository_state ON repository (state);
CREATE UNIQUE INDEX robotaccounttoken_robot_account_id ON robotaccounttoken (robot_account_id);
CREATE INDEX accesstoken_role_id ON accesstoken (role_id);
CREATE INDEX accesstoken_repository_id ON accesstoken (repository_id);
CREATE UNIQUE INDEX accesstoken_token_name ON accesstoken (token_name);
CREATE INDEX accesstoken_kind_id ON accesstoken (kind_id);
CREATE UNIQUE INDEX appspecificauthtoken_token_name ON appspecificauthtoken (token_name);
CREATE INDEX appspecificauthtoken_user_id ON appspecificauthtoken (user_id);
CREATE INDEX appspecificauthtoken_uuid ON appspecificauthtoken (uuid);
CREATE INDEX appspecificauthtoken_user_id_expiration ON appspecificauthtoken (user_id, expiration);
CREATE INDEX oauthaccesstoken_uuid ON oauthaccesstoken (uuid);
CREATE INDEX oauthaccesstoken_authorized_user_id ON oauthaccesstoken (authorized_user_id);
CREATE INDEX oauthaccesstoken_application_id ON oauthaccesstoken (application_id);
CREATE UNIQUE INDEX oauthaccesstoken_token_name ON oauthaccesstoken (token_name);
CREATE INDEX oauthapplication_client_id ON oauthapplication (client_id);
CREATE INDEX oauthapplication_organization_id ON oauthapplication (organization_id);
CREATE INDEX oauthauthorizationcode_application_id ON oauthauthorizationcode (application_id);
CREATE UNIQUE INDEX oauthauthorizationcode_code_name ON oauthauthorizationcode (code_name);
CREATE INDEX repositorybuildtrigger_service_id ON repositorybuildtrigger (service_id);
CREATE INDEX repositorybuildtrigger_disabled_reason_id ON repositorybuildtrigger (disabled_reason_id);
CREATE INDEX repositorybuildtrigger_uuid ON repositorybuildtrigger (uuid);
CREATE INDEX repositorybuildtrigger_pull_robot_id ON repositorybuildtrigger (pull_robot_id);
CREATE INDEX repositorybuildtrigger_repository_id ON repositorybuildtrigger (repository_id);
CREATE INDEX repositorybuildtrigger_write_token_id ON repositorybuildtrigger (write_token_id);
CREATE INDEX repositorybuildtrigger_disabled_datetime ON repositorybuildtrigger (disabled_datetime);
CREATE INDEX repositorybuildtrigger_connected_user_id ON repositorybuildtrigger (connected_user_id);
CREATE INDEX deletedrepository_original_name ON deletedrepository (original_name);
CREATE INDEX deletedrepository_queue_id ON deletedrepository (queue_id);
CREATE UNIQUE INDEX deletedrepository_repository_id ON deletedrepository (repository_id);
CREATE INDEX manifestsecuritystatus_index_status ON manifestsecuritystatus (index_status);
CREATE INDEX manifestsecuritystatus_indexer_hash ON manifestsecuritystatus (indexer_hash);
CREATE INDEX manifestsecuritystatus_indexer_version ON manifestsecuritystatus (indexer_version);
CREATE INDEX manifestsecuritystatus_last_indexed ON manifestsecuritystatus (last_indexed);
CREATE UNIQUE INDEX manifestsecuritystatus_manifest_id ON manifestsecuritystatus (manifest_id);
CREATE INDEX manifestsecuritystatus_repository_id ON manifestsecuritystatus (repository_id);
CREATE INDEX uploadedblob_blob_id ON uploadedblob (blob_id);
CREATE INDEX uploadedblob_expires_at ON uploadedblob (expires_at);
CREATE INDEX uploadedblob_repository_id ON uploadedblob (repository_id);
CREATE INDEX manifest_repository_id_config_media_type ON manifest (repository_id, config_media_type);
CREATE INDEX manifestblob_repository_id_blob_id ON manifestblob (repository_id, blob_id);
CREATE UNIQUE INDEX userorganizationquota_organization ON userorganizationquota (namespace_id);
CREATE INDEX quotalimits_quota_id ON quotalimits (quota_id);
CREATE INDEX repomirrorconfig_root_rule_id ON repomirrorconfig (root_rule_id);
CREATE UNIQUE INDEX repomirrorconfig_repository_id ON repomirrorconfig (repository_id);
CREATE INDEX repomirrorconfig_internal_robot_id ON repomirrorconfig (internal_robot_id);
CREATE INDEX repomirrorconfig_sync_transaction_id ON repomirrorconfig (sync_transaction_id);
CREATE INDEX repomirrorconfig_sync_status ON repomirrorconfig (sync_status);
CREATE INDEX repomirrorconfig_mirror_type ON repomirrorconfig (mirror_type);
CREATE INDEX user_robot ON user (robot);
CREATE INDEX user_uuid ON user (uuid);
CREATE INDEX user_organization ON user (organization);
CREATE INDEX user_last_accessed ON user (last_accessed);
CREATE UNIQUE INDEX user_username ON user (username);
CREATE UNIQUE INDEX user_email ON user (email);
CREATE INDEX user_stripe_id ON user (stripe_id);
CREATE INDEX user_invoice_email_address ON user (invoice_email_address);
CREATE UNIQUE INDEX organizationrhskus_subscription_id ON organizationrhskus (subscription_id);
CREATE UNIQUE INDEX organizationrhskus_subscription_id_org_id ON organizationrhskus (subscription_id, org_id);
CREATE UNIQUE INDEX organizationrhskus_subscription_id_org_id_user_id ON organizationrhskus (subscription_id, org_id, user_id);
CREATE UNIQUE INDEX quotanamespacesize_namespace_user_id ON quotanamespacesize (namespace_user_id);
CREATE INDEX quotanamespacesize_backfill_start_ms ON quotanamespacesize (backfill_start_ms);
CREATE INDEX quotanamespacesize_size_bytes ON quotanamespacesize (size_bytes);
CREATE UNIQUE INDEX quotarepositorysize_repository_id ON quotarepositorysize (repository_id);
CREATE INDEX quotarepositorysize_size_bytes ON quotarepositorysize (size_bytes);
CREATE UNIQUE INDEX namespaceautoprunepolicy_namespace_id ON namespaceautoprunepolicy (namespace_id);
CREATE UNIQUE INDEX namespaceautoprunepolicy_uuid ON namespaceautoprunepolicy (uuid);
CREATE UNIQUE INDEX autoprunetaskstatus_namespace_id ON autoprunetaskstatus (namespace_id);
CREATE INDEX autoprunetaskstatus_last_ran_ms ON autoprunetaskstatus (last_ran_ms);
CREATE UNIQUE INDEX repositoryautoprunepolicy_uuid ON repositoryautoprunepolicy (uuid);
CREATE UNIQUE INDEX repositoryautoprunepolicy_repository_id ON repositoryautoprunepolicy (repository_id);
CREATE INDEX repositoryautoprunepolicy_namespace_id ON repositoryautoprunepolicy (namespace_id);
CREATE INDEX manifest_repository_id_subject ON manifest (repository_id, subject);
CREATE INDEX manifest_subject_backfilled ON manifest (subject_backfilled);
CREATE UNIQUE INDEX oauthassignedtoken_uuid ON oauthassignedtoken (uuid);
CREATE INDEX oauthassignedtoken_application_id ON oauthassignedtoken (application_id);
CREATE INDEX oauthassignedtoken_assigned_user ON oauthassignedtoken (assigned_user_id);
CREATE INDEX tagnotificationsuccess_notification_id ON tagnotificationsuccess (notification_id);
CREATE INDEX tagnotificationsuccess_tag_id ON tagnotificationsuccess (tag_id);
CREATE INDEX repositorynotification_last_ran_ms ON repositorynotification (last_ran_ms);
CREATE INDEX manifest_repository_id_artifact_type ON manifest (repository_id, artifact_type);
CREATE INDEX manifest_artifact_type_backfilled ON manifest (artifact_type_backfilled);
COMMIT;
