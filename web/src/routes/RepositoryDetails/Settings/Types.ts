import {RepoRole} from 'src/resources/RepositoryResource';

export interface RoleOption {
  name: string;
  description: string;
  role: RepoRole;
}

export const roles: RoleOption[] = [
  {
    name: 'Read',
    description: 'Can view and pull from the repository',
    role: RepoRole.read,
  },
  {
    name: 'Write',
    description: 'Can view, pull, and push to the repository',
    role: RepoRole.write,
  },
  {
    name: 'Admin',
    description: 'Full admin access to the organization',
    role: RepoRole.admin,
  },
];
