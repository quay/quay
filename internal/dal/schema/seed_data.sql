-- Auto-generated from tools/export_schema_ddl.py SEED_DATA
-- DO NOT EDIT - run 'make go-schema' to regenerate

-- role
INSERT OR IGNORE INTO role (name) VALUES ('admin');
INSERT OR IGNORE INTO role (name) VALUES ('write');
INSERT OR IGNORE INTO role (name) VALUES ('read');

-- teamrole
INSERT OR IGNORE INTO teamrole (name) VALUES ('admin');
INSERT OR IGNORE INTO teamrole (name) VALUES ('creator');
INSERT OR IGNORE INTO teamrole (name) VALUES ('member');

-- visibility
INSERT OR IGNORE INTO visibility (name) VALUES ('public');
INSERT OR IGNORE INTO visibility (name) VALUES ('private');

-- loginservice
INSERT OR IGNORE INTO loginservice (name) VALUES ('google');
INSERT OR IGNORE INTO loginservice (name) VALUES ('github');
INSERT OR IGNORE INTO loginservice (name) VALUES ('quayrobot');
INSERT OR IGNORE INTO loginservice (name) VALUES ('ldap');
INSERT OR IGNORE INTO loginservice (name) VALUES ('jwtauthn');
INSERT OR IGNORE INTO loginservice (name) VALUES ('keystone');
INSERT OR IGNORE INTO loginservice (name) VALUES ('dex');
INSERT OR IGNORE INTO loginservice (name) VALUES ('oidc');

-- buildtriggerservice
INSERT OR IGNORE INTO buildtriggerservice (name) VALUES ('github');
INSERT OR IGNORE INTO buildtriggerservice (name) VALUES ('custom-git');
INSERT OR IGNORE INTO buildtriggerservice (name) VALUES ('bitbucket');
INSERT OR IGNORE INTO buildtriggerservice (name) VALUES ('gitlab');

-- accesstokenkind
INSERT OR IGNORE INTO accesstokenkind (name) VALUES ('build-worker');
INSERT OR IGNORE INTO accesstokenkind (name) VALUES ('pushpull-token');

-- repositorykind
INSERT OR IGNORE INTO repositorykind (name) VALUES ('image');

-- tagkind
INSERT OR IGNORE INTO tagkind (name) VALUES ('tag');

-- disablereason
INSERT OR IGNORE INTO disablereason (name) VALUES ('user_toggled');
INSERT OR IGNORE INTO disablereason (name) VALUES ('successive_build_failures');
INSERT OR IGNORE INTO disablereason (name) VALUES ('successive_build_internal_errors');

-- imagestoragelocation
INSERT OR IGNORE INTO imagestoragelocation (name) VALUES ('local_eu');
INSERT OR IGNORE INTO imagestoragelocation (name) VALUES ('local_us');

-- imagestoragetransformation
INSERT OR IGNORE INTO imagestoragetransformation (name) VALUES ('squash');
INSERT OR IGNORE INTO imagestoragetransformation (name) VALUES ('aci');

-- imagestoragesignaturekind
INSERT OR IGNORE INTO imagestoragesignaturekind (name) VALUES ('gpg2');

-- labelsourcetype
INSERT OR IGNORE INTO labelsourcetype (name) VALUES ('manifest');
INSERT OR IGNORE INTO labelsourcetype (name, mutable) VALUES ('api', 1);
INSERT OR IGNORE INTO labelsourcetype (name) VALUES ('internal');

-- userpromptkind
INSERT OR IGNORE INTO userpromptkind (name) VALUES ('confirm_username');
INSERT OR IGNORE INTO userpromptkind (name) VALUES ('enter_name');
INSERT OR IGNORE INTO userpromptkind (name) VALUES ('enter_company');

-- quayregion
INSERT OR IGNORE INTO quayregion (name) VALUES ('us');

-- quayservice
INSERT OR IGNORE INTO quayservice (name) VALUES ('quay');

-- mediatype
INSERT OR IGNORE INTO mediatype (name) VALUES ('text/plain');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/json');
INSERT OR IGNORE INTO mediatype (name) VALUES ('text/markdown');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/vnd.docker.distribution.manifest.v1+json');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/vnd.docker.distribution.manifest.v1+prettyjws');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/vnd.docker.distribution.manifest.v2+json');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/vnd.docker.distribution.manifest.list.v2+json');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/vnd.oci.image.manifest.v1+json');
INSERT OR IGNORE INTO mediatype (name) VALUES ('application/vnd.oci.image.index.v1+json');

-- externalnotificationevent
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('repo_push');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('build_queued');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('build_start');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('build_success');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('build_cancelled');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('build_failure');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('vulnerability_found');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('repo_mirror_sync_started');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('repo_mirror_sync_success');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('repo_mirror_sync_failed');
INSERT OR IGNORE INTO externalnotificationevent (name) VALUES ('repo_image_expiry');

-- externalnotificationmethod
INSERT OR IGNORE INTO externalnotificationmethod (name) VALUES ('quay_notification');
INSERT OR IGNORE INTO externalnotificationmethod (name) VALUES ('email');
INSERT OR IGNORE INTO externalnotificationmethod (name) VALUES ('webhook');
INSERT OR IGNORE INTO externalnotificationmethod (name) VALUES ('flowdock');
INSERT OR IGNORE INTO externalnotificationmethod (name) VALUES ('hipchat');
INSERT OR IGNORE INTO externalnotificationmethod (name) VALUES ('slack');

-- notificationkind
INSERT OR IGNORE INTO notificationkind (name) VALUES ('repo_push');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('build_queued');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('build_start');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('build_success');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('build_cancelled');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('build_failure');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('vulnerability_found');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('service_key_submitted');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('password_required');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('over_private_usage');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('expiring_license');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('maintenance');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('org_team_invite');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('repo_mirror_sync_started');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('repo_mirror_sync_success');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('repo_mirror_sync_failed');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('test_notification');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('quota_warning');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('quota_error');
INSERT OR IGNORE INTO notificationkind (name) VALUES ('assigned_authorization');

-- logentrykind
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_create');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_delete');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_disable');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_enable');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_change_email');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_change_password');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_change_name');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_change_invoicing');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_change_tag_expiration');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_change_metadata');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('user_generate_client_key');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('account_change_plan');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('account_change_cc');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('account_change_password');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('account_convert');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_robot');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_robot');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_robot_federation');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_robot_federation');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('federated_robot_token_exchange');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_repo');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('push_repo');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('push_repo_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('pull_repo');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('pull_repo_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repo');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_tag');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('move_tag');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_tag');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_tag_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('revert_tag');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('add_repo_permission');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_repo_permission');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repo_permission');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_repo_visibility');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_repo_trust');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('add_repo_accesstoken');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repo_accesstoken');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('set_repo_description');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_repo_state');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('build_dockerfile');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_create');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_create_team');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete_team');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_invite_team_member');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete_team_member_invite');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_add_team_member');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_team_member_invite_accepted');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_team_member_invite_declined');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_remove_team_member');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_set_team_description');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_set_team_role');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_email');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_invoicing');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_tag_expiration');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_name');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_prototype_permission');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('modify_prototype_permission');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_prototype_permission');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('setup_repo_trigger');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repo_trigger');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_application');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('update_application');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_application');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('reset_application_client_secret');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('add_repo_webhook');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repo_webhook');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('add_repo_notification');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repo_notification');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('reset_repo_notification');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('regenerate_robot_token');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_verb');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_enabled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_disabled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_config_changed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_started');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_now_requested');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_tag_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_tag_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_test_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_test_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('repo_mirror_sync_test_started');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_enabled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_disabled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_config_changed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_started');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_failed');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_now_requested');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_sync_cancelled');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_mirror_repo_created');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('service_key_create');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('service_key_approve');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('service_key_delete');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('service_key_modify');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('service_key_extend');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('service_key_rotate');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('take_ownership');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('manifest_label_add');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('manifest_label_delete');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_tag_expiration');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('change_tag_immutability');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('toggle_repo_trigger');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_immutability_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('update_immutability_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_immutability_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('tag_made_immutable_by_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('tags_made_immutable_by_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_app_specific_token');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('revoke_app_specific_token');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_proxy_cache_config');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_proxy_cache_config');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('start_build_trigger');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('cancel_build');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('login_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('login_failure');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('logout_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('permanently_delete_tag');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('autoprune_tag_delete');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_namespace_autoprune_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('update_namespace_autoprune_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_namespace_autoprune_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('create_repository_autoprune_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('update_repository_autoprune_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('delete_repository_autoprune_policy');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('enable_team_sync');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('disable_team_sync');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('oauth_token_assigned');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('oauth_token_revoked');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('export_logs_success');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('export_logs_failure');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_create_quota');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_quota');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete_quota');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_create_quota_limit');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_change_quota_limit');
INSERT OR IGNORE INTO logentrykind (name) VALUES ('org_delete_quota_limit');
