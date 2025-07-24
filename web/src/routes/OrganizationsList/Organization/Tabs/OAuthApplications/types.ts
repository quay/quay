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
  'repo:read': {
    scope: 'repo:read',
    icon: 'fa-eye',
    dangerous: false,
    title: 'View all visible repositories',
    description:
      'This application will be able to view and pull all repositories visible to your account',
  },
  'repo:write': {
    scope: 'repo:write',
    icon: 'fa-pencil',
    dangerous: true,
    title: 'Read/Write to any accessible repositories',
    description:
      'This application will be able to view, push and pull to all repositories visible to your account',
  },
  'repo:admin': {
    scope: 'repo:admin',
    icon: 'fa-gear',
    dangerous: true,
    title: 'Administer all visible repositories',
    description:
      'This application will have administrator access to all repositories visible to your account',
  },
  'repo:create': {
    scope: 'repo:create',
    icon: 'fa-plus',
    dangerous: true,
    title: 'Create new repositories',
    description:
      'This application will be able to create new repositories in any namespaces that your account has access to',
  },
  'user:read': {
    scope: 'user:read',
    icon: 'fa-user',
    dangerous: false,
    title: 'View user information',
    description:
      'This application will be able to view your basic user information such as username and email address',
  },
  'user:admin': {
    scope: 'user:admin',
    icon: 'fa-user-cog',
    dangerous: true,
    title: 'Administer your account',
    description:
      'This application will have administrator access to your user account including the ability to change passwords and create tokens',
  },
  'org:admin': {
    scope: 'org:admin',
    icon: 'fa-users-cog',
    dangerous: true,
    title: 'Administer your organizations',
    description:
      'This application will have administrator access to all organizations of which you are an administrator',
  },
};
