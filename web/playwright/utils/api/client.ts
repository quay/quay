/**
 * API client for Playwright e2e tests
 *
 * Provides API interactions with CSRF token caching to reduce redundant requests.
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';

export type RepositoryVisibility = 'public' | 'private';
export type RepositoryState = 'NORMAL' | 'MIRROR' | 'READ_ONLY';
export type TeamRole = 'member' | 'creator' | 'admin';
export type PrototypeRole = 'read' | 'write' | 'admin';

export interface MirrorConfig {
  external_reference: string;
  sync_interval: number;
  sync_start_date: string;
  root_rule: {
    rule_kind: 'tag_glob_csv';
    rule_value: string[];
  };
  robot_username: string;
  skopeo_timeout_interval?: number;
  is_enabled?: boolean;
  external_registry_username?: string | null;
  external_registry_password?: string | null;
  external_registry_config?: {
    verify_tls?: boolean;
    unsigned_images?: boolean;
    proxy?: {
      http_proxy?: string | null;
      https_proxy?: string | null;
      no_proxy?: string | null;
    };
  };
}

export interface MirrorConfigResponse extends MirrorConfig {
  sync_status: string;
  sync_retries_remaining: number;
  sync_expiration_date: string | null;
  mirror_type: string;
}

export interface CreateUserResponse {
  username: string;
  awaiting_verification?: boolean;
}

export interface CreateRobotResponse {
  name: string;
  token: string;
}

export interface PrototypeDelegate {
  name: string;
  kind: 'user' | 'team';
}

export interface PrototypeActivatingUser {
  name: string;
}

export interface Prototype {
  id: string;
  role: string;
  activating_user: {
    name: string;
    is_robot: boolean;
    kind: string;
    is_org_member: boolean;
  } | null;
  delegate: {
    name: string;
    kind: string;
  };
}

export interface GetPrototypesResponse {
  prototypes: Prototype[];
}

export class ApiClient {
  private request: APIRequestContext;
  private csrfToken: string | null = null;

  constructor(request: APIRequestContext) {
    this.request = request;
  }

  private async fetchToken(): Promise<string> {
    if (!this.csrfToken) {
      const response = await this.request.get(`${API_URL}/csrf_token`, {
        timeout: 5000,
      });
      if (!response.ok()) {
        throw new Error(`Failed to get CSRF token: ${response.status()}`);
      }
      const data = await response.json();
      this.csrfToken = data.csrf_token;
    }
    return this.csrfToken;
  }

  /**
   * Get the CSRF token (fetches if not cached)
   * Primarily for use by test fixtures that need the raw token.
   */
  async getToken(): Promise<string> {
    return this.fetchToken();
  }

  // Organization methods

  async createOrganization(
    name: string,
    email?: string,
  ): Promise<{name: string}> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          name,
          email: email || `${name}@example.com`,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create organization ${name}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async deleteOrganization(name: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${name}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete organization ${name}: ${response.status()} - ${body}`,
      );
    }
  }

  // Repository methods

  async createRepository(
    namespace: string,
    name: string,
    visibility: RepositoryVisibility = 'private',
    description = '',
  ): Promise<{namespace: string; name: string; kind: string}> {
    const token = await this.fetchToken();
    const response = await this.request.post(`${API_URL}/api/v1/repository`, {
      timeout: 5000,
      headers: {
        'X-CSRF-Token': token,
      },
      data: {
        namespace,
        repository: name,
        visibility,
        description,
        repo_kind: 'image',
      },
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create repository ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async deleteRepository(namespace: string, name: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/repository/${namespace}/${name}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete repository ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }
  }

  async changeRepositoryState(
    namespace: string,
    name: string,
    state: RepositoryState,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${name}/changestate`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          state,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to change repository state ${namespace}/${name} to ${state}: ${response.status()} - ${body}`,
      );
    }
  }

  // Repository mirroring methods

  async createMirrorConfig(
    namespace: string,
    name: string,
    config: MirrorConfig,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${name}/mirror`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          external_reference: config.external_reference,
          sync_interval: config.sync_interval,
          sync_start_date: config.sync_start_date,
          root_rule: config.root_rule,
          robot_username: config.robot_username,
          skopeo_timeout_interval: config.skopeo_timeout_interval ?? 300,
          is_enabled: config.is_enabled ?? true,
          external_registry_username: config.external_registry_username ?? null,
          external_registry_password: config.external_registry_password ?? null,
          external_registry_config: config.external_registry_config ?? {
            verify_tls: true,
            unsigned_images: false,
            proxy: {
              http_proxy: null,
              https_proxy: null,
              no_proxy: null,
            },
          },
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create mirror config for ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }
  }

  async getMirrorConfig(
    namespace: string,
    name: string,
  ): Promise<MirrorConfigResponse | null> {
    const response = await this.request.get(
      `${API_URL}/api/v1/repository/${namespace}/${name}/mirror`,
      {
        timeout: 5000,
      },
    );

    if (response.status() === 404) {
      return null;
    }

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get mirror config for ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async updateMirrorConfig(
    namespace: string,
    name: string,
    updates: Partial<MirrorConfig>,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${name}/mirror`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: updates,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to update mirror config for ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }
  }

  async triggerMirrorSync(namespace: string, name: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${name}/mirror/sync-now`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to trigger mirror sync for ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }
  }

  async cancelMirrorSync(namespace: string, name: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${name}/mirror/sync-cancel`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to cancel mirror sync for ${namespace}/${name}: ${response.status()} - ${body}`,
      );
    }
  }

  // Repository notification methods

  async createRepositoryNotification(
    namespace: string,
    repo: string,
    event: string,
    method: string,
    config: Record<string, unknown>,
    eventConfig: Record<string, unknown> = {},
    title?: string,
  ): Promise<{uuid: string}> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/notification/`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          event,
          method,
          config,
          eventConfig,
          title,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create repository notification: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  // Team methods

  async createTeam(
    orgName: string,
    teamName: string,
    role: TeamRole = 'member',
  ): Promise<{name: string; role: string}> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/organization/${orgName}/team/${teamName}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          role,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create team ${teamName} in ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async deleteTeam(orgName: string, teamName: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/team/${teamName}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete team ${teamName} from ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  // Robot account methods

  async createRobot(
    orgName: string,
    robotShortname: string,
    description = '',
  ): Promise<CreateRobotResponse> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/organization/${orgName}/robots/${robotShortname}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          description,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create robot ${robotShortname} in ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async deleteRobot(orgName: string, robotShortname: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/robots/${robotShortname}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete robot ${robotShortname} from ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  // Prototype (default permission) methods

  async getPrototypes(orgName: string): Promise<GetPrototypesResponse> {
    const response = await this.request.get(
      `${API_URL}/api/v1/organization/${orgName}/prototypes`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get prototypes for ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async createPrototype(
    orgName: string,
    role: PrototypeRole,
    delegate: PrototypeDelegate,
    activatingUser?: PrototypeActivatingUser,
  ): Promise<{id: string}> {
    const token = await this.fetchToken();

    const data: Record<string, unknown> = {
      role,
      delegate,
    };

    if (activatingUser) {
      data.activating_user = activatingUser;
    }

    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/prototypes`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create prototype in ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async deletePrototype(orgName: string, prototypeId: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/prototypes/${prototypeId}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete prototype ${prototypeId} from ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  // User methods

  async createUser(
    username: string,
    password: string,
    email: string,
  ): Promise<CreateUserResponse> {
    const token = await this.fetchToken();
    const response = await this.request.post(`${API_URL}/api/v1/user/`, {
      timeout: 10000,
      headers: {
        'X-CSRF-Token': token,
      },
      data: {
        username,
        password,
        email,
      },
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create user ${username}: ${response.status()} - ${body}`,
      );
    }

    const result = await response.json();
    return {
      username: result.username || username,
      awaiting_verification: result.awaiting_verification,
    };
  }

  async deleteUser(username: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/superuser/users/${username}`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete user ${username}: ${response.status()} - ${body}`,
      );
    }
  }

  async userExists(username: string): Promise<boolean> {
    const response = await this.request.get(
      `${API_URL}/api/v1/users/${username}`,
      {
        timeout: 5000,
      },
    );
    return response.ok();
  }

  // Auth methods

  async signIn(username: string, password: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(`${API_URL}/api/v1/signin`, {
      timeout: 5000,
      headers: {
        'X-CSRF-Token': token,
      },
      data: {
        username,
        password,
      },
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to sign in as ${username}: ${response.status()} - ${body}`,
      );
    }
  }

  // User notification methods

  async getUserNotifications(): Promise<{
    notifications: Array<{
      id: string;
      kind: string;
      metadata: {name: string; repository: string};
      dismissed: boolean;
    }>;
    additional: boolean;
  }> {
    const response = await this.request.get(
      `${API_URL}/api/v1/user/notifications`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get user notifications: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  // Team member methods (for test setup)

  async addTeamMember(
    orgName: string,
    teamName: string,
    memberName: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/organization/${orgName}/team/${teamName}/members/${memberName}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to add member ${memberName} to team ${teamName}: ${response.status()} - ${body}`,
      );
    }
  }

  async removeTeamMember(
    orgName: string,
    teamName: string,
    memberName: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/team/${teamName}/members/${memberName}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to remove member ${memberName} from team ${teamName}: ${response.status()} - ${body}`,
      );
    }
  }

  // Repository permission methods

  async addRepositoryPermission(
    namespace: string,
    repo: string,
    entityType: 'user' | 'team',
    entityName: string,
    role: PrototypeRole,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/permissions/${entityType}/${entityName}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          role,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to add ${entityType} permission for ${entityName} on ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  async deleteRepositoryPermission(
    namespace: string,
    repo: string,
    entityType: 'user' | 'team',
    entityName: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/permissions/${entityType}/${entityName}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
      },
    );

    if (!response.ok() && response.status() !== 404) {
      const body = await response.text();
      throw new Error(
        `Failed to delete ${entityType} permission for ${entityName} on ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }
}
