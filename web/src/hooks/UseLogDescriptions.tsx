import React from 'react';
import {isNullOrUndefined, humanizeTimeForExpiry} from 'src/libs/utils';
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

  const getConfigObject = (config: string | Config): Config => {
    if (typeof config === 'string') {
      try {
        return JSON.parse(config);
      } catch {
        return {};
      }
    }
    return config || {};
  };

  const getTriggerDescription = (service: string, config: string | Config) => {
    const configObj = getConfigObject(config);
    let buildSource = '';
    if (configObj) {
      buildSource = configObj.build_source || '';
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

  // Helper function to format service key names (mimics Angular's kid filter)
  const formatServiceKeyName = (metadata: Metadata) => {
    if (metadata.name) {
      return metadata.name;
    }
    return metadata.kid ? metadata.kid.substr(0, 12) : '';
  };

  // Helper function to format Unix timestamps (mimics Angular's date filters)
  const formatUnixTimestamp = (timestamp: string | number) => {
    if (!timestamp) return '';
    // Handle both string and number timestamps
    const unixTime =
      typeof timestamp === 'string' ? parseInt(timestamp) : timestamp;
    return new Date(unixTime * 1000).toLocaleString();
  };

  // Helper function to wrap variables with styling (mimics Angular's code tag styling)
  const wrapVariable = (
    value: string | React.ReactNode,
    className = 'log-variable',
  ) => {
    return (
      <code
        className={className}
        style={{
          padding: '2px 4px',
          borderRadius: '3px',
          fontFamily: 'monospace',
          fontSize: '0.9em',
          color: 'var(--pf-v5-global--Color--200)',
        }}
      >
        {value}
      </code>
    );
  };

  const descriptions = {
    user_create: function (metadata: Metadata) {
      if (metadata.superuser) {
        return (
          <>
            Superuser {wrapVariable(metadata.superuser)} created user{' '}
            {wrapVariable(metadata.username)}
          </>
        );
      } else {
        return <>User {wrapVariable(metadata.username)} created</>;
      }
    },
    user_delete: function (metadata: Metadata) {
      if (metadata.superuser) {
        return (
          <>
            Superuser {wrapVariable(metadata.superuser)} deleted user{' '}
            {wrapVariable(metadata.username)}
          </>
        );
      } else {
        return <>User {wrapVariable(metadata.username)} deleted</>;
      }
    },
    user_enable: function (metadata: Metadata) {
      if (metadata.superuser) {
        return (
          <>
            Superuser {wrapVariable(metadata.superuser)} enabled user{' '}
            {wrapVariable(metadata.username)}
          </>
        );
      } else {
        return <>User {wrapVariable(metadata.username)} enabled</>;
      }
    },
    user_disable: function (metadata: Metadata) {
      if (metadata.superuser) {
        return (
          <>
            Superuser {wrapVariable(metadata.superuser)} disabled user{' '}
            {wrapVariable(metadata.username)}
          </>
        );
      } else {
        return <>User {wrapVariable(metadata.username)} disabled</>;
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
    user_change_tag_expiration: function (metadata: Metadata) {
      const humanizedTime = humanizeTimeForExpiry(
        parseInt(metadata.tag_expiration),
      );
      return `Change time machine window to ${humanizedTime}`;
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
      return <>Create Robot Account {wrapVariable(metadata.robot)}</>;
    },
    delete_robot: function (metadata: Metadata) {
      return <>Delete Robot Account {wrapVariable(metadata.robot)}</>;
    },
    create_repo: function (metadata: Metadata) {
      return (
        <>
          Create Repository{' '}
          {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
        </>
      );
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
      return (
        <>
          Repository state changed to{' '}
          {wrapVariable(metadata.state_changed.toUpperCase())}
        </>
      );
    },
    push_repo: function (metadata: Metadata) {
      if (metadata.tag) {
        return (
          <>
            Push of {wrapVariable(metadata.tag)} to repository{' '}
            {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
          </>
        );
      } else if (metadata.release) {
        return (
          <>
            Push of {wrapVariable(metadata.release)} to repository{' '}
            {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
          </>
        );
      } else {
        return (
          <>
            Repository push to{' '}
            {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
          </>
        );
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
      return <>Delete repository {wrapVariable(metadata.repo)}</>;
    },
    change_repo_permission: function (metadata: Metadata) {
      if (metadata.username) {
        return (
          <>
            Change permission for user {wrapVariable(metadata.username)} in
            repository {wrapVariable(metadata.repo)} to{' '}
            {wrapVariable(metadata.role)}
          </>
        );
      } else if (metadata.team) {
        return (
          <>
            Change permission for team {wrapVariable(metadata.team)} in
            repository {wrapVariable(metadata.repo)} to{' '}
            {wrapVariable(metadata.role)}
          </>
        );
      } else if (metadata.token) {
        return (
          <>
            Change permission for token {wrapVariable(metadata.token)} in
            repository {wrapVariable(metadata.repo)} to{' '}
            {wrapVariable(metadata.role)}
          </>
        );
      }
    },
    delete_repo_permission: function (metadata: Metadata) {
      if (metadata.username) {
        return (
          <>
            Remove permission for user {wrapVariable(metadata.username)} from
            repository {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
          </>
        );
      } else if (metadata.team) {
        return (
          <>
            Remove permission for team {wrapVariable(metadata.team)} from
            repository {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
          </>
        );
      } else if (metadata.token) {
        return (
          <>
            Remove permission for token {wrapVariable(metadata.token)} from
            repository {wrapVariable(`${metadata.namespace}/${metadata.repo}`)}
          </>
        );
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
      return (
        <>
          Tag {wrapVariable(metadata.tag)} pruned in repository{' '}
          {wrapVariable(`${metadata.namespace}/${metadata.repo}`)} by{' '}
          {wrapVariable(metadata.performer)}
        </>
      );
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
      return (
        <>
          Tag {wrapVariable(metadata.tag)} deleted in repository{' '}
          {wrapVariable(`${metadata.namespace}/${metadata.repo}`)} by user{' '}
          {wrapVariable(metadata.username)}
        </>
      );
    },
    permanently_delete_tag: function (metadata: Metadata) {
      if (metadata.manifest_digest) {
        return `Tag ${metadata.tag} referencing ${metadata.manifest_digest} permanently deleted in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
      } else {
        return `Tag ${metadata.tag} permanently deleted in repository ${metadata.namespace}/${metadata.repo} by user ${metadata.username}`;
      }
    },
    create_tag: function (metadata: Metadata) {
      return (
        <>
          Tag {wrapVariable(metadata.tag)} created in repository{' '}
          {wrapVariable(`${metadata.namespace}/${metadata.repo}`)} on image{' '}
          {wrapVariable(metadata.image)} by user{' '}
          {wrapVariable(metadata.username)}
        </>
      );
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
      return (
        <>
          Create access token {wrapVariable(metadata.token)} in repository{' '}
          {wrapVariable(metadata.repo)}
        </>
      );
    },
    delete_repo_accesstoken: function (metadata: Metadata) {
      return (
        <>
          Delete access token {wrapVariable(metadata.token)} in repository{' '}
          {wrapVariable(metadata.repo)}
        </>
      );
    },
    set_repo_description: function (metadata: Metadata) {
      return `Change description for repository ${metadata.namespace}/${metadata.repo} to ${metadata.description}`;
    },
    build_dockerfile: function (metadata: Metadata) {
      if (metadata.trigger_id) {
        const triggerDescription = getTriggerDescription(
          metadata.service,
          (metadata.config as string | Config) || '',
        );
        return (
          `Build from Dockerfile for repository ${metadata.namespace}/${metadata.repo} triggered by ` +
          triggerDescription
        );
      }
      return `Build from Dockerfile for repository ${metadata.namespace}/${metadata.repo}`;
    },
    org_create: function (metadata: Metadata) {
      return <>Organization {wrapVariable(metadata.namespace)} created</>;
    },
    org_delete: function (metadata: Metadata) {
      return <>Organization {wrapVariable(metadata.namespace)} deleted</>;
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
      const humanizedTime = humanizeTimeForExpiry(
        parseInt(metadata.tag_expiration),
      );
      return `Change time machine window to ${humanizedTime}`;
    },
    org_change_name: function (metadata: Metadata) {
      if (metadata.superuser) {
        return `Superuser ${metadata.superuser} renamed organization from ${metadata.old_name} to ${metadata.new_name}`;
      } else {
        return `Organization renamed from ${metadata.old_name} to ${metadata.new_name}`;
      }
    },
    org_create_team: function (metadata: Metadata) {
      return <>Create team {wrapVariable(metadata.team)}</>;
    },
    org_delete_team: function (metadata: Metadata) {
      return <>Delete team {wrapVariable(metadata.team)}</>;
    },
    org_add_team_member: function (metadata: Metadata) {
      return (
        <>
          Add member {wrapVariable(metadata.member)} to team{' '}
          {wrapVariable(metadata.team)}
        </>
      );
    },
    org_remove_team_member: function (metadata: Metadata) {
      return (
        <>
          Remove member {wrapVariable(metadata.member)} from team{' '}
          {wrapVariable(metadata.team)}
        </>
      );
    },
    org_invite_team_member: function (metadata: Metadata) {
      if (metadata.user) {
        return (
          <>
            Invite {wrapVariable(metadata.user)} to team{' '}
            {wrapVariable(metadata.team)}
          </>
        );
      } else {
        return (
          <>
            Invite {wrapVariable(metadata.email)} to team{' '}
            {wrapVariable(metadata.team)}
          </>
        );
      }
    },
    org_delete_team_member_invite: function (metadata: Metadata) {
      if (metadata.user) {
        return (
          <>
            Rescind invite of {wrapVariable(metadata.user)} to team{' '}
            {wrapVariable(metadata.team)}
          </>
        );
      } else {
        return (
          <>
            Rescind invite of {wrapVariable(metadata.email)} to team{' '}
            {wrapVariable(metadata.team)}
          </>
        );
      }
    },

    org_team_member_invite_accepted: function (metadata: Metadata) {
      return (
        <>
          User {wrapVariable(metadata.member)}, invited by{' '}
          {wrapVariable(metadata.inviter)}, joined team{' '}
          {wrapVariable(metadata.team)}
        </>
      );
    },
    org_team_member_invite_declined: function (metadata: Metadata) {
      return (
        <>
          User {wrapVariable(metadata.member)}, invited by{' '}
          {wrapVariable(metadata.inviter)}, declined to join team{' '}
          {wrapVariable(metadata.team)}
        </>
      );
    },

    org_set_team_description: function (metadata: Metadata) {
      return (
        <>
          Change description of team {wrapVariable(metadata.team)} to{' '}
          {wrapVariable(metadata.description)}
        </>
      );
    },
    org_set_team_role: function (metadata: Metadata) {
      return (
        <>
          Change permission of team {wrapVariable(metadata.team)} to{' '}
          {wrapVariable(metadata.role)}
        </>
      );
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
        (metadata.config as string | Config) || '',
      );
      return 'Setup build trigger - ' + triggerDescription;
    },
    delete_repo_trigger: function (metadata: Metadata) {
      const triggerDescription = getTriggerDescription(
        metadata.service,
        (metadata.config as string | Config) || '',
      );
      return 'Delete build trigger - ' + triggerDescription;
    },
    toggle_repo_trigger: function (metadata: Metadata) {
      const triggerDescription = getTriggerDescription(
        metadata.service,
        (metadata.config as string | Config) || '',
      );
      if (metadata.enabled) {
        return 'Build trigger enabled - ' + triggerDescription;
      } else {
        return 'Build trigger disabled - ' + triggerDescription;
      }
    },
    create_application: function (metadata: Metadata) {
      return (
        <>
          Create application {wrapVariable(metadata.application_name)} with{' '}
          client ID {wrapVariable(metadata.client_id)}
        </>
      );
    },
    update_application: function (metadata: Metadata) {
      return (
        <>
          Update application to {wrapVariable(metadata.application_name)} for{' '}
          client ID {wrapVariable(metadata.client_id)}
        </>
      );
    },
    delete_application: function (metadata: Metadata) {
      return (
        <>
          Delete application {wrapVariable(metadata.application_name)} with{' '}
          client ID {wrapVariable(metadata.client_id)}
        </>
      );
    },
    reset_application_client_secret: function (metadata: Metadata) {
      return (
        <>
          Reset the client secret of application{' '}
          {wrapVariable(metadata.application_name)} with client ID{' '}
          {wrapVariable(metadata.client_id)}
        </>
      );
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
      return <>Regenerated token for robot {wrapVariable(metadata.robot)}</>;
    },

    service_key_create: function (metadata: Metadata) {
      const keyName = formatServiceKeyName(metadata);
      if (metadata.preshared) {
        return (
          <>
            Manual creation of preshared service key {wrapVariable(keyName)} for
            service {wrapVariable(metadata.service)}
          </>
        );
      } else {
        return (
          <>
            Creation of service key {wrapVariable(keyName)} for service{' '}
            {wrapVariable(metadata.service)} by{' '}
            {wrapVariable(metadata.user_agent)}
          </>
        );
      }
    },

    service_key_approve: function (metadata: Metadata) {
      return (
        <>
          Approval of service key {wrapVariable(formatServiceKeyName(metadata))}
        </>
      );
    },
    service_key_modify: function (metadata: Metadata) {
      return (
        <>
          Modification of service key{' '}
          {wrapVariable(formatServiceKeyName(metadata))}
        </>
      );
    },
    service_key_delete: function (metadata: Metadata) {
      return (
        <>
          Deletion of service key {wrapVariable(formatServiceKeyName(metadata))}
        </>
      );
    },
    service_key_extend: function (metadata: Metadata) {
      const keyName = formatServiceKeyName(metadata);
      const oldDate = formatUnixTimestamp(metadata.old_expiration_date);
      const newDate = formatUnixTimestamp(metadata.expiration_date);
      return (
        <>
          Change of expiration of service key {wrapVariable(keyName)} from{' '}
          {wrapVariable(oldDate)} to {wrapVariable(newDate)}
        </>
      );
    },
    service_key_rotate: function (metadata: Metadata) {
      return (
        <>
          Automatic rotation of service key{' '}
          {wrapVariable(formatServiceKeyName(metadata))} by{' '}
          {wrapVariable(metadata.user_agent)}
        </>
      );
    },

    take_ownership: function (metadata: Metadata) {
      if (metadata.was_user) {
        return (
          <>
            Superuser {wrapVariable(metadata.superuser)} took ownership of user
            namespace {wrapVariable(metadata.namespace)}
          </>
        );
      } else {
        return (
          <>
            Superuser {wrapVariable(metadata.superuser)} took ownership of
            organization {wrapVariable(metadata.namespace)}
          </>
        );
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
        const newDate = formatUnixTimestamp(metadata.expiration_date);
        const oldDate = formatUnixTimestamp(metadata.old_expiration_date);
        return `Tag ${metadata.tag} set to expire on ${newDate} (previously ${oldDate})`;
      } else if (metadata.expiration_date) {
        const newDate = formatUnixTimestamp(metadata.expiration_date);
        return `Tag ${metadata.tag} set to expire on ${newDate}`;
      } else if (metadata.old_expiration_date) {
        const oldDate = formatUnixTimestamp(metadata.old_expiration_date);
        return `Tag ${metadata.tag} set to no longer expire (previously ${oldDate})`;
      } else {
        return `Tag ${metadata.tag} set to no longer expire`;
      }
    },

    create_app_specific_token: function (metadata: Metadata) {
      return (
        <>
          Created external application token{' '}
          {wrapVariable(metadata.app_specific_token_title)}
        </>
      );
    },
    revoke_app_specific_token: function (metadata: Metadata) {
      return (
        <>
          Revoked external application token{' '}
          {wrapVariable(metadata.app_specific_token_title)}
        </>
      );
    },
    repo_mirror: function (metadata: Metadata) {
      if (metadata.message) {
        return `Repository mirror ${metadata.verb} by Skopeo: ${metadata.message}`;
      } else {
        return `Repository mirror ${metadata.verb} by Skopeo`;
      }
    },
    start_build_trigger: function (metadata: Metadata) {
      const triggerDescription = getTriggerDescription(
        metadata.service,
        (metadata.config as string | Config) || '',
      );
      return 'Manually start build from trigger - ' + triggerDescription;
    },
    cancel_build: function (metadata: Metadata) {
      return `Cancel build ${metadata.build_uuid}`;
    },
    pull_repo_failed: function (metadata: Metadata) {
      let message = `Pull from repository ${metadata.namespace}/${metadata.repo} failed`;

      if (metadata.tag) {
        message += ` for tag ${metadata.tag}`;
      } else if (metadata.manifest_digest) {
        message += ` for manifest ${metadata.manifest_digest}`;
      }

      if (metadata.message) {
        message += ` with message ${metadata.message}`;
      }

      return message;
    },
    push_repo_failed: function (metadata: Metadata) {
      let message = `Push to repository ${metadata.namespace}/${metadata.repo} failed`;

      if (metadata.tag) {
        message += ` for tag ${metadata.tag}`;
      } else if (metadata.manifest_digest) {
        message += ` for manifest ${metadata.manifest_digest}`;
      }

      if (metadata.message) {
        message += ` with message ${metadata.message}`;
      }

      return message;
    },
    delete_tag_failed: function (metadata: Metadata) {
      let message = `Delete tag ${metadata.namespace}/${metadata.repo} failed`;

      if (metadata.tag) {
        message += ` for tag ${metadata.tag}`;
      } else if (metadata.manifest_digest) {
        message += ` for manifest ${metadata.manifest_digest}`;
      }

      if (metadata.message) {
        message += ` with message ${metadata.message}`;
      }

      return message;
    },
    create_proxy_cache_config: function (metadata: Metadata) {
      return `Create proxy cache for ${metadata.namespace} with upstream ${metadata.upstream_registry}`;
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
      if (metadata.type == 'v2auth') {
        if (metadata.kind == 'app_specific_token') {
          return (
            <>
              Login to registry with app-specific token{' '}
              {wrapVariable(metadata.app_specific_token_title)}
            </>
          );
        } else if (metadata.kind == 'robot') {
          return (
            <>Login to registry with robot {wrapVariable(metadata.robot)}</>
          );
        } else {
          return 'Login to registry';
        }
      } else {
        return 'Login to Quay';
      }
    },
    logout_success: function () {
      return 'Logout from Quay';
    },
    login_failure: function (metadata: Metadata) {
      if (metadata.type == 'v2auth') {
        let message = 'Login to registry failed';

        if (metadata.kind == 'app_specific_token') {
          message += ` with app-specific token`;
          if (metadata.app_specific_token_title) {
            message += ` ${metadata.app_specific_token_title}`;
          }
          if (metadata.username) {
            message += ` (owned by ${metadata.username})`;
          }
        } else if (metadata.kind == 'robot') {
          message += ` with robot ${metadata.robot}`;
          if (metadata.username) {
            message += ` (owned by ${metadata.username})`;
          }
        } else if (metadata.kind == 'user') {
          message += ` with user ${metadata.username}`;
        }

        if (metadata.message) {
          message += ` with message: ${metadata.message}`;
        }

        return message;
      } else if (metadata.type == 'quayauth') {
        if (metadata.kind == 'user') {
          let message = 'Login to Quay failed';
          if (metadata.username) {
            message += ` with username ${metadata.username}`;
          }
          if (metadata.message) {
            message += ` with message: ${metadata.message}`;
          }
          return message;
        } else if (metadata.kind == 'oauth') {
          let message = 'API access to Quay failed';
          if (metadata.token) {
            message += ` with token ${metadata.token}`;
            if (metadata.username && metadata.application_name) {
              message += ` (owned by ${metadata.username} in application ${metadata.application_name})`;
            }
          }
          if (metadata.message) {
            message += ` with message: ${metadata.message}`;
          }
          return message;
        }
      } else {
        return 'Login to Quay failed';
      }
    },
    oauth_token_assigned: function (metadata) {
      return (
        <>
          OAuth token assigned to user {wrapVariable(metadata.assigned_user)} by{' '}
          {wrapVariable(metadata.assigning_user)} for application{' '}
          {wrapVariable(metadata.application)}
        </>
      );
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
    org_create_quota: function (metadata: Metadata) {
      return (
        <>
          Created storage quota of {wrapVariable(metadata.limit)} for
          organization {wrapVariable(metadata.namespace)}
        </>
      );
    },
    org_change_quota: function (metadata: Metadata) {
      return (
        <>
          Changed storage quota for organization{' '}
          {wrapVariable(metadata.namespace)} from{' '}
          {wrapVariable(metadata.previous_limit)} to{' '}
          {wrapVariable(metadata.limit)}
        </>
      );
    },
    org_delete_quota: function (metadata: Metadata) {
      return (
        <>
          Deleted storage quota of {wrapVariable(metadata.limit)} for
          organization {wrapVariable(metadata.namespace)}
        </>
      );
    },
    org_create_quota_limit: function (metadata: Metadata) {
      return (
        <>
          Created {wrapVariable(metadata.type)} quota limit at{' '}
          {wrapVariable(`${metadata.threshold_percent}%`)} for organization{' '}
          {wrapVariable(metadata.namespace)}
        </>
      );
    },
    org_change_quota_limit: function (metadata: Metadata) {
      return (
        <>
          Changed quota limit for organization{' '}
          {wrapVariable(metadata.namespace)}: {wrapVariable(metadata.type)}{' '}
          threshold from{' '}
          {wrapVariable(`${metadata.previous_threshold_percent}%`)} to{' '}
          {wrapVariable(`${metadata.threshold_percent}%`)}
        </>
      );
    },
    org_delete_quota_limit: function (metadata: Metadata) {
      return (
        <>
          Deleted {wrapVariable(metadata.type)} quota limit at{' '}
          {wrapVariable(`${metadata.threshold_percent}%`)} for organization{' '}
          {wrapVariable(metadata.namespace)}
        </>
      );
    },
  };

  return descriptions;
}

function obfuscate_email(email: string) {
  const email_array = email.split('@');
  return (
    email_array[0].substring(0, 2) +
    '*'.repeat(email_array[0].length - 2) +
    '@' +
    email_array[1]
  );
}
