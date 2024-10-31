import {isNullOrUndefined} from 'src/libs/utils';
import {useEvents} from './UseEvents';

export function useLogDescriptions() {
  const events = useEvents();

  interface Metadata {
    [key: string]: string;
  }

  interface Config {
    [key: string]: string;
  }

  const defaultPermSuffix = (metadata: Metadata) => {
    if (metadata.activating_username) {
      return ', when creating user is {activating_username}';
    }
    return '';
  };

  const getTriggerDescription = (service: string, config: Config) => {
    let buildSource = '';
    if (config) {
      buildSource = config.build_source;
    }

    switch (service) {
      case 'github':
        return `push to GitHub ${buildSource}`;
      case 'bitbucket':
        return `push to BitBucket repository ${buildSource}`;
      case 'gitlab':
        return `push to GitLab repository ${buildSource} `;
      case 'custom-git':
        return `push to repository ${buildSource}`;
      default:
        return '';
    }
  };

  const autoPrunePolicyDescription = (metadata: Metadata) => {
    let policyMessage = `${metadata.method}:${metadata.value}`;
    if (!isNullOrUndefined(metadata.tag_pattern)) {
      policyMessage += `, tagPattern:${
        metadata.tag_pattern
      }, tagPatternMatches:${
        isNullOrUndefined(metadata.tag_pattern_matches) ||
        metadata.tag_pattern_matches
          ? 'true'
          : 'false'
      }`;
    }
    return policyMessage;
  };

  const descriptions = {
    user_create: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} created user ${metadata.username}`;
      } else {
        return `User ${metadata.username} created`;
      }
    },
    user_delete: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} deleted user ${metadata.username}`;
      } else {
        return `User ${metadata.username} deleted`;
      }
    },
    user_enable: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} enabled user ${metadata.username}`;
      } else {
        return `User ${metadata.username} enabled`;
      }
    },
    user_disable: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} disabled user ${metadata.username}`;
      } else {
        return `User ${metadata.username} disabled`;
      }
    },
    user_change_password: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} changed password of user ${metadata.username}`;
      } else {
        return `User ${metadata.username} changed password`;
      }
    },
    user_change_email: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} changed email from ${metadata.old_email} to ${metadata.email}`;
      } else {
        return `Changed email from ${metadata.old_email} to ${metadata.email}`;
      }
    },
    user_change_name: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} renamed user ${metadata.old_username} to ${metadata.username}`;
      } else {
        return `User ${metadata.old_username} changed name to ${metadata.username}`;
      }
    },
    user_change_invoicing: function (metadata: Metadata) {
      if (metadata.invoice_email) {
        return `Enabled email invoicing`;
      } else if (metadata.invoice_email_address) {
        return `Set email invoicing address to ${metadata.invoice_email_address}`;
      } else {
        return `Disabled email invoicing`;
      }
    },
    user_generate_client_key: function () {
      return 'Generated Docker CLI password';
    },
    user_change_metadata: function () {
      return 'User changed metadata';
    },
    user_change_tag_expiration: function () {
      return 'Change time machine window to {tag_expiration}';
    },
    account_change_plan: function () {
      return 'Change plan';
    },
    account_change_cc: function () {
      return 'Update credit card';
    },
    account_change_password: function () {
      return 'Change password';
    },
    account_convert: function () {
      return 'Convert account to organization';
    },
    create_robot: function (metadata: Metadata) {
      return `Create Robot Account ${metadata.robot}`;
    },
    delete_robot: function (metadata: Metadata) {
      return `Delete Robot Account ${metadata.robot}`;
    },
    create_repo: function (metadata: Metadata) {
      return `Create Repository ${metadata.namespace}/${metadata.repo}`;
    },
    repo_mirror_sync_started: function (metadata: Metadata) {
      return `Mirror started for ${metadata.message}`;
    },
    repo_mirror_sync_success: function (metadata: Metadata) {
      return `Mirror finished successfully for ${metadata.message} ${metadata.tags}`;
    },
    repo_mirror_sync_failed: function (metadata: Metadata) {
      return `Mirror finished unsuccessfully for ${metadata.message} ${metadata.tags} ${metadata.stdout} ${metadata.stderr}`;
    },
    repo_mirror_sync_tag_success: function (metadata: Metadata) {
      return `Mirror of ${metadata.tag} successful to repository ${metadata.namespace}/${metadata.repo} ${metadata.message} ${metadata.stdout} ${metadata.stderr}`;
    },
    repo_mirror_sync_tag_failed: function (metadata: Metadata) {
      return `Mirror of ${metadata.tag} failure to repository ${metadata.namespace}/${metadata.repo} ${metadata.message} ${metadata.stdout} ${metadata.stderr}`;
    },
    repo_mirror_config_changed: function (metadata: Metadata) {
      switch (metadata.changed) {
        case 'sync_status':
          if (metadata.to === 'SYNC_CANCEL') {
            return 'Mirror canceled';
          } else if (metadata.to === 'SYNC_NOW') {
            return 'Immediate mirror scheduled';
          } else {
            return `Mirror ${metadata.changed} changed to ${metadata.to}`;
          }
        case 'sync_start_date':
          metadata.changed = 'Sync Start Date';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'sync_interval':
          metadata.changed = 'Sync Interval';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'external_registry':
          metadata.changed = 'External Registry';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'mirror_rule':
          metadata.changed = 'Tags';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'is_enabled':
          metadata.changed = 'Enabled';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'robot_username':
          metadata.changed = 'Robot User';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'external_registry_username':
          metadata.changed = 'External Registry Username';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'external_registry_password':
          metadata.changed = 'External Registry Password';
          return 'Mirror {changed} changed to {to}';
        case 'verify_tls':
          metadata.changed = 'Verify TLS';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'unsigned_images':
          metadata.changed = 'Accept Unsigned Images';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'http_proxy':
          metadata.changed = 'HTTP_PROXY';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'https_proxy':
          metadata.changed = 'HTTPS_PROXY';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        case 'no_proxy':
          metadata.changed = 'NO_PROXY';
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
        default:
          return `Mirror ${metadata.changed} changed to ${metadata.to}`;
      }
    },
    change_repo_state: function (metadata: Metadata) {
      return `Repository state changed to ${metadata.state_changed
        .toLowerCase()
        .replace('_', ' ')}`;
    },
    push_repo: function (metadata: Metadata) {
      if (metadata.tag) {
        return `Push of ${metadata.tag} to repository ${metadata.namespace}/${metadata.repo}`;
      } else if (metadata.release) {
        return `Push of ${metadata.release} to repository ${metadata.namespace}/${metadata.repo}`;
      } else {
        return `Repository push to ${metadata.namespace}/${metadata.repo}`;
      }
    },
    repo_verb: function (metadata: Metadata) {
      let prefix = '';
      if (metadata.verb == 'squash') {
        prefix = `Pull of squashed tag ${metadata.tag} from ${metadata.namespace}/${metadata.repo}`;
      } else if (metadata.verb == 'aci') {
        prefix = `Pull of ACI of tag ${metadata.tag} from ${metadata.namespace}/${metadata.repo}`;
      } else {
        prefix = `Pull of tag ${metadata.tag} from ${metadata.namespace}/${metadata.repo}`;
      }

      if (metadata.token) {
        if (metadata.token_type == 'build-worker') {
          prefix += `by build worker`;
        } else {
          prefix += ' via token';
        }
      } else if (metadata.username) {
        prefix += ` by ${metadata.username}`;
      } else {
        prefix += ` by ${metadata._ip}`;
      }

      return prefix;
    },
    pull_repo: function (metadata: Metadata) {
      let description = `repository ${metadata.namespace}/${metadata.repo}`;
      if (metadata.tag) {
        description = `tag ${metadata.tag} from repository ${metadata.namespace}/${metadata.repo}`;
      } else if (metadata.manifest_digest) {
        description = `digest ${metadata.manifest_digest} from repository ${metadata.namespace}/${metadata.repo}`;
      } else if (metadata.release) {
        description = `release ${metadata.release}`;
        if (metadata.channel) {
          description += ` via channel ${metadata.channel}`;
        }
        if (metadata.mediatype) {
          description += ` for ${metadata.mediatype}`;
        }
        description += ` from repository ${metadata.namespace}/${metadata.repo}`;
      }

      if (metadata.token) {
        if (metadata.token_type == 'build-worker') {
          return 'Pull of ' + description + 'by build worker';
        } else {
          return 'Pull of ' + description + ' via token';
        }
      } else if (metadata.username) {
        return 'Pull ' + description + ` by ${metadata.username}`;
      } else {
        return 'Public pull of ' + description + `by ${metadata._ip}`;
      }
    },
    delete_repo: function (metadata: Metadata) {
      return `Delete repository ${metadata.repo}`;
    },
    change_repo_permission: function (metadata: Metadata) {
      if (metadata.username) {
        return `Change permission for user ${metadata.username} in repository ${metadata.repo} to ${metadata.role}`;
      } else if (metadata.team) {
        return `Change permission for team ${metadata.team} in repository ${metadata.repo} to ${metadata.role}`;
      } else if (metadata.token) {
        return `Change permission for token ${metadata.token} in repository ${metadata.repo} to ${metadata.role}`;
      }
    },
    delete_repo_permission: function (metadata: Metadata) {
      if (metadata.username) {
        return `Remove permission for user ${metadata.username} from repository ${metadata.namespace}/${metadata.repo}`;
      } else if (metadata.team) {
        return `Remove permission for team ${metadata.team}  from repository ${metadata.namespace}/${metadata.repo}`;
      } else if (metadata.token) {
        return `Remove permission for token ${metadata.token} from repository ${metadata.namespace}/${metadata.repo}`;
      }
    },
    revert_tag: function (metadata: Metadata) {
      if (metadata.manifest_digest) {
        return `Tag ${metadata.tag} restored to ${metadata.manifest_digest}`;
      } else {
        return `Tag ${metadata.tag} restored to ${metadata.image}`;
      }
    },
    autoprune_tag_delete: function (metadata: Metadata) {
      return `Tag ${metadata.tag} pruned in repository ${metadata.namespace}/${metadata.repo} by ${metadata.performer}`;
    },
    create_namespace_autoprune_policy: function (metadata: Metadata) {
      return `Created namespace autoprune policy: "${autoPrunePolicyDescription(
        metadata,
      )}" for namespace: ${metadata.namespace}`;
    },
    update_namespace_autoprune_policy: function (metadata: Metadata) {
      return `Updated namespace autoprune policy: "${autoPrunePolicyDescription(
        metadata,
      )}" for namespace: ${metadata.namespace}`;
    },
    delete_namespace_autoprune_policy: function (metadata: Metadata) {
      return `Deleted namespace autoprune policy for namespace:${metadata.namespace}`;
    },
    create_repository_autoprune_policy: function (metadata: Metadata) {
      return `Created repository autoprune policy: "${autoPrunePolicyDescription(
        metadata,
      )}" for repository: ${metadata.namespace}/${metadata.repo}`;
    },
    update_repository_autoprune_policy: function (metadata: Metadata) {
      return `Updated repository autoprune policy: "${autoPrunePolicyDescription(
        metadata,
      )}" for repository: ${metadata.namespace}/${metadata.repo}`;
    },
    delete_repository_autoprune_policy: function (metadata: Metadata) {
      return `Deleted repository autoprune policy for repository: ${metadata.namespace}/${metadata.repo}`;
    },
    delete_tag: function (metadata: Metadata) {
      return `Tag ${metadata.tag} deleted in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
    },
    permanently_delete_tag: function (metadata: Metadata) {
      if (metadata.manifest_digest) {
        return `Tag ${metadata.tag} referencing ${metadata.manifest_digest} permanently deleted in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
      } else {
        return `Tag ${metadata.tag} permanently deleted in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
      }
    },
    create_tag: function (metadata: Metadata) {
      return `Tag ${metadata.tag} created in repository ${metadata.namespace}/${metadata.repo} on image ${metadata.image} by user ${metadata.username}`;
    },
    move_tag: function (metadata: Metadata) {
      if (metadata.manifest_digest) {
        return `Tag ${metadata.tag} moved from ${metadata.original_manifest_digest} to ${metadata.manifest_digest} in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
      } else {
        return `Tag ${metadata.tag} moved from image ${metadata.original_image} to image ${metadata.image} in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
      }
    },
    change_repo_visibility: function (metadata: Metadata) {
      return `Change visibility for repository ${metadata.namespace}/${metadata.repo} to ${metadata.visibility}`;
    },
    change_repo_trust: function (metadata: Metadata) {
      if (metadata.trust_enabled) {
        return `Trust enabled for ${metadata.namespace}/${metadata.repo}`;
      } else {
        return `Trust disabled for ${metadata.namespace}/${metadata.repo}`;
      }
    },
    add_repo_accesstoken: function (metadata: Metadata) {
      return `Create access token ${metadata.token} in repository ${metadata.repo}`;
    },
    delete_repo_accesstoken: function (metadata: Metadata) {
      return `Delete access token ${metadata.token} in repository ${metadata.repo}`;
    },
    set_repo_description: function (metadata: Metadata) {
      return `Change description for repository ${metadata.namespace}/${metadata.repo} to ${metadata.description}`;
    },
    build_dockerfile: function (metadata: Metadata) {
      if (metadata.trigger_id) {
        const triggerDescription = getTriggerDescription(
          metadata['service'],
          metadata['config'],
        );
        return (
          `Build from Dockerfile for repository ${metadata.namespace}/${metadata.repo} triggered by ` +
          triggerDescription
        );
      }
      return `Build from Dockerfile for repository ${metadata.namespace}/${metadata.repo}`;
    },
    org_create: function (metadata: Metadata) {
      return `Organization ${metadata.namespace} created`;
    },
    org_delete: function (metadata: Metadata) {
      return `Organization ${metadata.namespace} deleted`;
    },
    org_change_email: function (metadata: Metadata) {
      return `Change organization email from ${metadata.old_email} to ${metadata.email}`;
    },
    org_change_invoicing: function (metadata: Metadata) {
      if (metadata.invoice_email) {
        return 'Enabled email invoicing';
      } else if (metadata.invoice_email_address) {
        return `Set email invoicing address to ${metadata.invoice_email_address}`;
      } else {
        return 'Disabled email invoicing';
      }
    },
    org_change_tag_expiration: function (metadata: Metadata) {
      `Change time machine window to ${metadata.tag_expiration}`;
    },
    org_change_name: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} renamed organization from ${metadata.old_name} to ${metadata.new_name}`;
      } else {
        return `Organization renamed from ${metadata.old_name} to ${metadata.new_name}`;
      }
    },
    org_create_team: function (metadata: Metadata) {
      return `Create team ${metadata.team}`;
    },
    org_delete_team: function (metadata: Metadata) {
      return `Delete team ${metadata.team}`;
    },
    org_add_team_member: function (metadata: Metadata) {
      return `Add member ${metadata.member} to team ${metadata.team}`;
    },
    org_remove_team_member: function (metadata: Metadata) {
      return `Remove member ${metadata.member} from team ${metadata.team}`;
    },
    org_invite_team_member: function (metadata: Metadata) {
      if (metadata.user) {
        return `Invite ${metadata.user} to team ${metadata.team}`;
      } else {
        return `Invite ${metadata.email} to team ${metadata.team}`;
      }
    },
    org_delete_team_member_invite: function (metadata: Metadata) {
      if (metadata.user) {
        return `Rescind invite of ${metadata.user} to team ${metadata.team}`;
      } else {
        return `Rescind invite of ${metadata.email} to team ${metadata.team}`;
      }
    },

    org_team_member_invite_accepted: function (metadata: Metadata) {
      return `User ${metadata.member}, invited by ${metadata.inviter}, joined team ${metadata.team}`;
    },
    org_team_member_invite_declined: function (metadata: Metadata) {
      return `User ${metadata.member}, invited by ${metadata.inviter}, declined to join team ${metadata.team}`;
    },

    org_set_team_description: function (metadata: Metadata) {
      return `Change description of team ${metadata.team} to ${metadata.description}`;
    },
    org_set_team_role: function (metadata: Metadata) {
      return `Change permission of team ${metadata.team} to ${metadata.role}`;
    },
    create_prototype_permission: function (metadata: Metadata) {
      if (metadata.delegate_user) {
        return (
          `Create default permission: ${metadata.role} for ${metadata.delegate_user}` +
          defaultPermSuffix(metadata)
        );
      } else if (metadata.delegate_team) {
        return (
          `Create default permission: ${metadata.role} for ${metadata.delegate_team}` +
          defaultPermSuffix(metadata)
        );
      }
    },
    modify_prototype_permission: function (metadata: Metadata) {
      if (metadata.delegate_user) {
        return (
          `Modify default permission: ${metadata.role} (from ${metadata.original_role}) for ${metadata.delegate_user}` +
          defaultPermSuffix(metadata)
        );
      } else if (metadata.delegate_team) {
        return (
          `Modify default permission: ${metadata.role} (from ${metadata.original_role}) for ${metadata.delegate_team}` +
          defaultPermSuffix(metadata)
        );
      }
    },
    delete_prototype_permission: function (metadata: Metadata) {
      if (metadata.delegate_user) {
        return (
          `Delete default permission: ${metadata.role} for ${metadata.delegate_user}` +
          defaultPermSuffix(metadata)
        );
      } else if (metadata.delegate_team) {
        return (
          `Delete default permission: ${metadata.role} for ${metadata.delegate_team}` +
          defaultPermSuffix(metadata)
        );
      }
    },
    setup_repo_trigger: function (metadata: Metadata) {
      const triggerDescription = getTriggerDescription(
        metadata.service,
        metadata.config,
      );
      return 'Setup build trigger - ' + triggerDescription;
    },
    delete_repo_trigger: function (metadata: Metadata) {
      const triggerDescription = getTriggerDescription(
        metadata['service'],
        metadata['config'],
      );
      return 'Delete build trigger - ' + triggerDescription;
    },
    toggle_repo_trigger: function (metadata: Metadata) {
      const triggerDescription = getTriggerDescription(
        metadata['service'],
        metadata['config'],
      );
      if (metadata.enabled) {
        return 'Build trigger enabled - ' + triggerDescription;
      } else {
        return 'Build trigger disabled - ' + triggerDescription;
      }
    },
    create_application: function (metadata: Metadata) {
      return `Create application ${metadata.application_name} with client ID ${metadata.client_id}`;
    },
    update_application: function (metadata: Metadata) {
      return `Update application to ${metadata.application_name} for client ID ${metadata.client_id}`;
    },
    delete_application: function (metadata: Metadata) {
      return `Delete application ${metadata.application_name} with client ID ${metadata.client_id}`;
    },
    reset_application_client_secret: function (metadata: Metadata) {
      return `Reset the client secret of application ${metadata.application_name} with client ID ${metadata.client_id}`;
    },
    add_repo_notification: function (metadata: Metadata) {
      const event = events.events.find((e) => e.type == metadata.event);
      return `Add notification of event "${event.title}" for repository ${metadata.namespace}/${metadata.repo}`;
    },

    delete_repo_notification: function (metadata: Metadata) {
      const event = events.events.find((e) => e.type == metadata.event);
      return `Delete notification of event ${event.title}  for repository ${metadata.namespace}/${metadata.repo}`;
    },

    reset_repo_notification: function (metadata: Metadata) {
      const event = events.events.find((e) => e.type == metadata.event);
      return `Re-enable notification of event ${event.title} for repository ${metadata.namespace}/${metadata.repo}`;
    },

    regenerate_robot_token: function (metadata: Metadata) {
      return `Regenerated token for robot ${metadata.robot}`;
    },

    service_key_create: function (metadata: Metadata) {
      if (metadata.preshared) {
        return `Manual creation of preshared service key ${metadata.kid} for service ${metadata.service}`;
      } else {
        return `Creation of service key ${metadata.kid} for service ${metadata.service} by ${metadata.user_agent}`;
      }
    },

    service_key_approve: function (metadata: Metadata) {
      `Approval of service key ${metadata.kid}`;
    },
    service_key_modify: function (metadata: Metadata) {
      `Modification of service key ${metadata.kid}`;
    },
    service_key_delete: function (metadata: Metadata) {
      `Deletion of service key ${metadata.kid}`;
    },
    service_key_extend: function (metadata: Metadata) {
      `Change of expiration of service key ${metadata.kid} from ${metadata.old_expiration_date}] to ${metadata.expiration_date}`;
    },
    service_key_rotate: function (metadata: Metadata) {
      `Automatic rotation of service key ${metadata.kid} by ${metadata.user_agent}`;
    },

    take_ownership: function (metadata: Metadata) {
      if (metadata.was_user) {
        return `Superuser ${metadata.superuser} took ownership of user namespace ${metadata.namespace}`;
      } else {
        return `Superuser ${metadata.superuser} took ownership of organization ${metadata.namespace}`;
      }
    },

    manifest_label_add: function (metadata: Metadata) {
      return `Label ${metadata.key} added to manifest ${metadata.manifest_digest} under repository ${metadata.namespace}/${metadata.repo}`;
    },
    manifest_label_delete: function (metadata: Metadata) {
      return `Label ${metadata.key} deleted from manifest ${metadata.manifest_digest} under repository ${metadata.namespace}/${metadata.repo}`;
    },

    change_tag_expiration: function (metadata: Metadata) {
      if (metadata.expiration_date && metadata.old_expiration_date) {
        return `Tag ${metadata.tag} set to expire on ${metadata.expiration_date} (previously ${metadata.old_expiration_date})`;
      } else if (metadata.expiration_date) {
        return `Tag ${metadata.tag} set to expire on ${metadata.expiration_date}`;
      } else if (metadata.old_expiration_date) {
        return `Tag ${metadata.tag} set to no longer expire (previously ${metadata.old_expiration_date})`;
      } else {
        return `Tag ${metadata.tag} set to no longer expire`;
      }
    },

    create_app_specific_token: function (metadata: Metadata) {
      return `Created external application token ${metadata.app_specific_token_title}`;
    },
    revoke_app_specific_token: function (metadata: Metadata) {
      return `Revoked external application token ${metadata.app_specific_token_title}`;
    },
    repo_mirror: function (metadata: Metadata) {
      if (metadata.message) {
        return `Repository mirror ${metadata.verb} by Skopeo: ${metadata.message}`;
      } else {
        return `Repository mirror ${metadata.verb} by Skopeo`;
      }
    },
    create_proxy_cache_config: function (metadata: Metadata) {
      return 'Created proxy cache for namespace';
    },
    delete_proxy_cache_config: function () {
      return 'Deleted proxy cache for namespace';
    },
    enable_team_sync: function (metadata: Metadata) {
      return `Team syncing enabled for ${metadata.team}`;
    },
    disable_team_sync: function (metadata: Metadata) {
      return `Team syncing disabled for ${metadata.team}`;
    },
    login_success: function (metadata: Metadata) {
      return `Successful login`;
    },
    oauth_token_assigned: function (metadata) {
      return `OAuth token assigned to user ${metadata.assigned_user} by ${metadata.assigning_user} for application ${metadata.application}`;
    },
    export_logs_success: function (metadata: Metadata) {
      if (metadata.repo) {
        if (metadata.url) {
          return `Logs export queued for delivery: id ${metadata.export_id}, url: ${metadata.url}, repository: ${metadata.repo}`;
        } else if (metadata.email) {
          return `Logs export queued for delivery: id ${
            metadata.export_id
          }, email: ${obfuscate_email(metadata.email)}, repository: ${
            metadata.repo
          }`;
        } else {
          return `Logs export queued for delivery: id ${
            metadata.export_id
          }, url: ${metadata.url}, email: ${obfuscate_email(
            metadata.email,
          )}, repository: ${metadata.repo}`;
        }
      } else {
        if (metadata.url) {
          return `User/organization logs export queued for delivery: id ${metadata.export_id}, url: ${metadata.url}`;
        } else if (metadata.email) {
          return `User/organization logs export queued for delivery: id ${
            metadata.export_id
          }, email: ${obfuscate_email(metadata.email)}`;
        } else {
          return `User/organization logs export queued for delivery: id ${
            metadata.export_id
          }, url: ${metadata.url}, email: ${obfuscate_email(metadata.email)}`;
        }
      }
    },
    export_logs_failure: function (metadata: Metadata) {
      return `Export logs failure: ${metadata.error}, ${
        metadata.repo ? `requested repository: ${metadata.repo}` : ''
      }`;
    },
    create_robot_federation: function (metadata: Metadata) {
      return `Create robot federation for robot ${metadata.robot}`;
    },
    delete_robot_federation: function (metadata: Metadata) {
      return `Delete robot federation for robot ${metadata.robot}`;
    },
    federated_robot_token_exchange: function (metadata: Metadata) {
      return `Federated robot token exchange robot:${metadata.robot}, issuer:${metadata.issuer}, subject:${metadata.subject}`;
    },
  };

  return descriptions;
}

function obfuscate_email(email: Array) {
  const email_array = email.split('@');
  return (
    email_array[0].substring(0, 2) +
    '*'.repeat(email_array[0].length - 2) +
    '@' +
    email_array[1]
  );
}
