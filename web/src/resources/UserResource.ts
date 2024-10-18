import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {IAvatar, IOrganization} from './OrganizationResource';

export interface IUserResource {
  anonymous: boolean;
  username: string;
  avatar: IAvatar;
  can_create_repo: boolean;
  is_me: boolean;
  verified: true;
  email: string;
  logins: [
    {
      service: string;
      service_identifier: string;
      metadata: {
        service_username: string;
      };
    },
  ];
  invoice_email: boolean;
  invoice_email_address: string;
  preferred_namespace: boolean;
  tag_expiration_s: number;
  prompts: [];
  super_user: boolean;
  company: string;
  family_name: string;
  given_name: string;
  location: string;
  is_free_account: boolean;
  has_password_set: boolean;
  organizations: IOrganization[];
}

export async function fetchUser() {
  const response: AxiosResponse<IUserResource> =
    await axios.get('/api/v1/user/');
  assertHttpCode(response.status, 200);
  return response.data;
}

export interface AllUsers {
  users: IUserResource[];
}

export async function fetchUsersAsSuperUser() {
  const superUserOrgsUrl = `/api/v1/superuser/users/`;
  const response: AxiosResponse<AllUsers> = await axios.get(superUserOrgsUrl);
  assertHttpCode(response.status, 200);
  return response.data?.users;
}

export interface Entity {
  avatar?: IAvatar;
  is_org_member?: boolean;
  name: string;
  kind?: EntityKind;
  is_robot?: boolean;
  can_read?: boolean;
}

export enum EntityKind {
  user = 'user',
  robot = 'robot',
  team = 'team',
  organization = 'organization',
}

interface EntitiesResponse {
  results: Entity[];
}

export function getEntityKind(entity: Entity) {
  if (entity.kind == EntityKind.team) {
    return EntityKind.team;
  } else if (entity.kind == EntityKind.user && entity.is_robot) {
    return EntityKind.robot;
  } else if (entity.kind == EntityKind.user) {
    return EntityKind.user;
  }
}

export async function fetchEntities(
  searchInput: string,
  org: string,
  includeTeams?: boolean,
) {
  // Handles the case of robot accounts, API doesn't recognize anything before the + sign
  if (searchInput.indexOf('+') > -1) {
    const splitSearchTerm = searchInput.split('+');
    searchInput = splitSearchTerm.length > 1 ? splitSearchTerm[1] : '';
  }
  const searchUrl = includeTeams
    ? `/api/v1/entities/${searchInput}?namespace=${org}&includeTeams=true`
    : `/api/v1/entities/${searchInput}?namespace=${org}`;

  const response: AxiosResponse<EntitiesResponse> = await axios.get(searchUrl);

  assertHttpCode(response.status, 200);
  return response.data?.results;
}

export interface UpdateUserRequest {
  username?: string;
  invoice_email?: boolean;
  family_name?: string;
  location?: string;
  company?: string;
  password?: string;
  invoice_email_address?: string;
  tag_expiration_s?: number;
  email?: string;
}

export async function updateUser(updateUserRequest: UpdateUserRequest) {
  const response: AxiosResponse<IUserResource> = await axios.put(
    'api/v1/user/',
    {...updateUserRequest},
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function createClientKey(password: string): Promise<string> {
  const updateUserUrl = `/api/v1/user/clientkey`;
  const response = await axios.post(updateUserUrl, {password});
  assertHttpCode(response.status, 200);
  return response.data.key;
}

export interface ConvertUserRequest {
  plan?: string;
  adminUser: string;
  adminPassword: string;
}

export async function convert(
  convertUserRequest: ConvertUserRequest,
): Promise<void> {
  const updateUserUrl = `/api/v1/user/convert`;
  const response = await axios.post(updateUserUrl, convertUserRequest);
  assertHttpCode(response.status, 200);
}
