import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';
import {IAvatar, IOrganization} from './OrganizationResource';
import {MemberType} from './RepositoryResource';

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
  const response: AxiosResponse<IUserResource> = await axios.get(
    '/api/v1/user/',
  );
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
  avatar: IAvatar;
  is_org_member: boolean;
  name: string;
  kind: string;
  is_robot?: boolean;
}

interface EntitiesResponse {
  results: Entity[];
}

export function getMemberType(entity: Entity) {
  if (entity.kind == MemberType.team) {
    return MemberType.team;
  } else if (entity.kind == MemberType.user && entity.is_robot) {
    return MemberType.robot;
  } else if (entity.kind == MemberType.user) {
    return MemberType.user;
  }
}

export async function fetchEntities(org: string, search: string) {
  // Handles the case of robot accounts, API doesn't recognize anything before the + sign
  if (search.indexOf('+') > -1) {
    const splitSearchTerm = search.split('+');
    search = splitSearchTerm.length > 1 ? splitSearchTerm[1] : '';
  }
  const response: AxiosResponse<EntitiesResponse> = await axios.get(
    `/api/v1/entities/${search}?namespace=${org}&includeTeams=true`,
  );
  assertHttpCode(response.status, 200);
  return response.data?.results;
}
