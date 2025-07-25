export interface OAuthApplicationFormData {
  name: string;
  application_uri: string;
  description: string;
  avatar_email: string;
  redirect_uri: string;
}

export const defaultOAuthFormValues: OAuthApplicationFormData = {
  name: '',
  application_uri: '',
  description: '',
  avatar_email: '',
  redirect_uri: '',
};

export interface OAuthScope {
  scope: string;
  icon: string;
  dangerous: boolean;
  title: string;
  description: string;
}

export const OAUTH_SCOPES: Record<string, OAuthScope> = {
  'org:admin': {
    scope: 'org:admin',
    icon: 'fa-gear',
    dangerous: true,
    title: 'Administer Organization',
    description:
      'This application will be able to administer your organizations including creating robots, creating teams, adjusting team membership, and changing billing settings. You should have absolute trust in the requesting application before granting this permission.',
  },
  'repo:admin': {
    scope: 'repo:admin',
    icon: 'fa-hdd-o',
    dangerous: false,
    title: 'Administer Repositories',
    description:
      'This application will have administrator access to all repositories to which the granting user has access',
  },
  'repo:create': {
    scope: 'repo:create',
    icon: 'fa-plus',
    dangerous: false,
    title: 'Create Repositories',
    description:
      'This application will be able to create repositories in all namespaces that the granting user is allowed to create repositories',
  },
  'repo:read': {
    scope: 'repo:read',
    icon: 'fa-hdd-o',
    dangerous: false,
    title: 'View all visible repositories',
    description:
      'This application will be able to view and pull all repositories visible to the granting user',
  },
  'repo:write': {
    scope: 'repo:write',
    icon: 'fa-hdd-o',
    dangerous: false,
    title: 'Read/Write to any accessible repositories',
    description:
      'This application will be able to view, push and pull to all repositories to which the granting user has write access',
  },
  'super:user': {
    scope: 'super:user',
    icon: 'fa-street-view',
    dangerous: true,
    title: 'Super User Access',
    description:
      'This application will be able to administer your installation including managing users, managing organizations and other features found in the superuser panel. You should have absolute trust in the requesting application before granting this permission.',
  },
  'user:admin': {
    scope: 'user:admin',
    icon: 'fa-gear',
    dangerous: true,
    title: 'Administer User',
    description:
      'This application will be able to administer your account including creating robots and granting them permissions to your repositories. You should have absolute trust in the requesting application before granting this permission.',
  },
  'user:read': {
    scope: 'user:read',
    icon: 'fa-user',
    dangerous: false,
    title: 'Read User Information',
    description:
      'This application will be able to read user information such as username and email address.',
  },
};
