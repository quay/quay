export const notificationTemplates: Record<
  string,
  string | ((metadata: any) => string)
> = {
  repo_push: (metadata) => {
    if (metadata.updated_tags && metadata.updated_tags.length) {
      return `Repository "${
        metadata.repository
      }" has been pushed with the following tags updated: "${metadata.updated_tags.join(
        ', ',
      )}"`;
    } else {
      return `Repository ${metadata.repository} has been pushed`;
    }
  },
  vulnerability_found: (metadata) => {
    return `A ${metadata.vulnerability.priority} vulnerability was detected in repository "${metadata.repository}"`;
  },
  build_failure: (metadata) => {
    return `A build has failed for repository "${metadata.repository}"`;
  },
  build_queued: (metadata) => {
    return `A build has been queued for repository "${metadata.repository}"`;
  },
  build_start: (metadata) => {
    return `A build has been started for repository "${metadata.repository}"`;
  },
  build_success: (metadata) => {
    return `A build has succeeded for repository "${metadata.repository}"`;
  },
  build_cancelled: (metadata) => {
    return `A build was cancelled for repository "${metadata.repository}"`;
  },
  repo_mirror_sync_started: (metadata) => {
    if (metadata.message && Object.keys(metadata.message).length) {
      return `Repository Mirror started for "${metadata.message}"`;
    } else {
      return `Repository Mirror started for "${metadata.repository}"`;
    }
  },
  repo_mirror_sync_success: (metadata) => {
    if (metadata.message && Object.keys(metadata.message).length) {
      return `Repository Mirror successful for "${metadata.message}"`;
    } else {
      return `Repository Mirror successful for "${metadata.repository}"`;
    }
  },
  repo_mirror_sync_failed: (metadata) => {
    if (metadata.message && Object.keys(metadata.message).length) {
      return `Repository Mirror unsuccessful for "${metadata.message}"`;
    } else {
      return `Repository Mirror unsuccessful for "${metadata.repository}"`;
    }
  },
  repo_image_expiry: (metadata) => {
    return `Images in repository "${metadata.repository}" will expire in ${metadata.days} days`;
  },
  quota_warning: (metadata) => {
    return `"${metadata.namespace}" quota has exceeded warning limit`;
  },
  quota_error: (metadata) => {
    return `"${metadata.namespace}" quota has been exceeded`;
  },
  maintenance: (metadata) => {
    return `We will be down for scheduled maintenance from ${metadata.from_date} to ${metadata.to_date} for ${metadata.reason}. We are sorry about any inconvenience.`;
  },
  service_key_submitted: (metadata) => {
    return `Service key "${metadata.kid}" for service "${metadata.service}" requests approval. Key was created on ${metadata.created_date}`;
  },
  assigned_authorization: () => {
    return `You have been assigned an Oauth authorization. Please approve or deny the request.`;
  },
  org_team_invite: (metadata) => {
    return `"${metadata.inviter}" is inviting you to join team "${metadata.team}" under organization "${metadata.org}"`;
  },
  password_required: () => {
    return `In order to begin pushing and pulling repositories, a password must be set for your account`;
  },
  over_private_usage: (metadata) => {
    return `Namespace "${metadata.namespace}" is over its allowed private repository count. Please upgrade your plan to avoid disruptions in service.`;
  },
  test_notification: (metadata) => {
    return `This notification is a long message for testing: ${metadata.obj}`;
  },
};

// for browser notifications - just return plain text
export function getNotificationMessage(notification: {
  kind: string;
  metadata?: any;
}): string {
  const template = notificationTemplates[notification.kind];
  if (!template) {
    return `(Unknown notification kind: ${notification.kind})`;
  }
  if (typeof template === 'function') {
    return template(notification.metadata || {});
  }
  return template;
}

const mirrorKinds = [
  'repo_mirror_sync_started',
  'repo_mirror_sync_success',
  'repo_mirror_sync_failed',
];

const buildKinds = [
  'build_queued',
  'build_start',
  'build_success',
  'build_failure',
  'build_cancelled',
];

// Links each kind to the most specific React page its stored metadata names,
// falling back to the repository or namespace page.
export function getNotificationLink(notification: {
  kind: string;
  metadata?: any;
}): string | null {
  const metadata = notification.metadata;
  if (!metadata) {
    return null;
  }
  const {kind} = notification;
  if (kind === 'quota_warning' || kind === 'quota_error') {
    return metadata.namespace
      ? `/organization/${metadata.namespace}?tab=Settings`
      : null;
  }
  if (!metadata.repository) {
    return metadata.namespace ? `/organization/${metadata.namespace}` : null;
  }
  const repositoryPage = `/repository/${metadata.repository}`;
  const tagPage = (tag: string) => `${repositoryPage}/tag/${tag}`;
  const tags: string[] = metadata.updated_tags ?? metadata.tags ?? [];
  if (kind === 'repo_push') {
    if (tags.length === 1) {
      return tagPage(tags[0]);
    }
    return tags.length ? `${repositoryPage}?tab=history` : repositoryPage;
  }
  if (kind === 'vulnerability_found') {
    // Every tag in the payload points at the one scanned manifest; a digest
    // stands in for the tag when the manifest has none.
    if (tags.length && !tags[0].includes(':')) {
      return `${tagPage(tags[0])}?tab=securityreport`;
    }
    return `${repositoryPage}?tab=tags`;
  }
  if (kind === 'repo_image_expiry') {
    return tags.length === 1 ? tagPage(tags[0]) : `${repositoryPage}?tab=tags`;
  }
  if (mirrorKinds.includes(kind)) {
    return `${repositoryPage}?tab=mirroring`;
  }
  if (buildKinds.includes(kind) && metadata.build_id) {
    return `${repositoryPage}/build/${metadata.build_id}`;
  }
  return repositoryPage;
}
