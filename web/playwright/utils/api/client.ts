/**
 * API client for Playwright e2e tests
 *
 * Provides API interactions with CSRF token caching to reduce redundant requests.
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';

export type RepositoryVisibility = 'public' | 'private';
export type RepositoryState = 'NORMAL' | 'MIRROR' | 'READ_ONLY';
export type OrgMirrorVisibility = 'public' | 'private';
export type TeamRole = 'member' | 'creator' | 'admin';
export type PrototypeRole = 'read' | 'write' | 'admin';
export type MessageSeverity = 'info' | 'warning' | 'error';
export type MessageMediaType = 'text/plain' | 'text/markdown';

// Immutability policy types
export interface ImmutabilityPolicy {
  uuid?: string;
  tagPattern: string;
  tagPatternMatches: boolean;
}

// Tag types
export interface TagInfo {
  name: string;
  manifest_digest: string;
  is_manifest_list: boolean;
  size: number;
  last_modified?: string;
  expiration?: string;
  start_ts?: number;
  end_ts?: number;
  reversion: boolean;
  immutable?: boolean;
}

export interface GetTagsResponse {
  tags: TagInfo[];
  page: number;
  has_additional: boolean;
}

// Organization mirror types
export interface OrgMirrorConfig {
  external_registry_type: 'harbor' | 'quay';
  external_registry_url: string;
  external_namespace: string;
  robot_username?: string | null;
  visibility: OrgMirrorVisibility;
  sync_interval: number;
  sync_start_date?: string | null;
  is_enabled?: boolean;
  external_registry_username?: string | null;
  external_registry_password?: string | null;
  external_registry_config?: {
    verify_tls?: boolean;
    proxy?: {
      http_proxy?: string | null;
      https_proxy?: string | null;
      no_proxy?: string | null;
    };
  };
  repository_filters?: string[];
  skopeo_timeout?: number;
}

export interface OrgMirrorConfigResponse extends OrgMirrorConfig {
  sync_status: string;
  sync_retries_remaining: number;
  sync_expiration_date: string | null;
  creation_date: string | null;
}

// Repository-level mirror types
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
  architecture_filter?: string[] | null;
}

export interface MirrorConfigResponse extends MirrorConfig {
  sync_status: string;
  sync_retries_remaining: number;
  sync_expiration_date: string | null;
  mirror_type: string;
  architecture_filter: string[];
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

// Global message types
export interface GlobalMessage {
  uuid: string;
  content: string;
  media_type: MessageMediaType;
  severity: MessageSeverity;
}

export interface GlobalMessagesResponse {
  messages: GlobalMessage[];
}

// Service key types
export interface ServiceKeyApproval {
  approval_type: string;
  approver?: {
    name: string;
    username: string;
    kind: string;
  };
  notes?: string;
}

export interface ServiceKey {
  kid: string;
  name?: string;
  service: string;
  created_date: string | number;
  expiration_date?: string | number;
  approval?: ServiceKeyApproval;
  metadata?: Record<string, unknown>;
}

export interface ServiceKeysResponse {
  keys: ServiceKey[];
}

// Quota types
export interface QuotaLimit {
  id: string;
  type: 'Warning' | 'Reject';
  limit_percent: number;
}

export interface Quota {
  id: string;
  limit_bytes: number;
  limits: QuotaLimit[];
}

// Proxy cache types
export interface ProxyCacheConfig {
  upstream_registry: string;
  expiration_s?: number;
  insecure?: boolean;
  upstream_registry_username?: string;
  upstream_registry_password?: string;
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
          architecture_filter: config.architecture_filter ?? null,
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

  async deleteRepositoryNotification(
    namespace: string,
    repo: string,
    uuid: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/notification/${uuid}`,
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
        `Failed to delete repository notification ${uuid}: ${response.status()} - ${body}`,
      );
    }
  }

  async enableRepositoryNotification(
    namespace: string,
    repo: string,
    uuid: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/notification/${uuid}`,
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
        `Failed to enable repository notification ${uuid}: ${response.status()} - ${body}`,
      );
    }
  }

  async testRepositoryNotification(
    namespace: string,
    repo: string,
    uuid: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/notification/${uuid}/test`,
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
        `Failed to test repository notification ${uuid}: ${response.status()} - ${body}`,
      );
    }
  }

  async getRepositoryNotifications(
    namespace: string,
    repo: string,
  ): Promise<{
    notifications: Array<{
      uuid: string;
      title: string;
      event: string;
      method: string;
      number_of_failures: number;
    }>;
  }> {
    const response = await this.request.get(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/notification/`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get repository notifications: ${response.status()} - ${body}`,
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

  /**
   * Create a user as superuser (requires superuser API context).
   * Returns the generated temporary password.
   */
  async createUserAsSuperuser(
    username: string,
    email?: string,
  ): Promise<{username: string; email?: string; password: string}> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/superuser/users/`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          username,
          email,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create user as superuser ${username}: ${response.status()} - ${body}`,
      );
    }

    const result = await response.json();
    return {
      username: result.username,
      email: result.email,
      password: result.password,
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

  // Global message methods (superuser only)

  async getMessages(): Promise<GlobalMessage[]> {
    const response = await this.request.get(`${API_URL}/api/v1/messages`, {
      timeout: 5000,
    });

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(`Failed to get messages: ${response.status()} - ${body}`);
    }

    const data: GlobalMessagesResponse = await response.json();
    return data.messages || [];
  }

  async createMessage(
    content: string,
    severity: MessageSeverity = 'info',
    mediaType: MessageMediaType = 'text/markdown',
  ): Promise<GlobalMessage> {
    const token = await this.fetchToken();
    const response = await this.request.post(`${API_URL}/api/v1/messages`, {
      timeout: 5000,
      headers: {
        'X-CSRF-Token': token,
      },
      data: {
        message: {
          content,
          media_type: mediaType,
          severity,
        },
      },
    });

    if (response.status() !== 201) {
      const body = await response.text();
      throw new Error(
        `Failed to create message: ${response.status()} - ${body}`,
      );
    }

    // API doesn't return the created message, so fetch to get the UUID
    const messages = await this.getMessages();
    const created = messages.find((m) => m.content === content);
    if (!created) {
      throw new Error('Created message not found after creation');
    }
    return created;
  }

  async deleteMessage(uuid: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/message/${uuid}`,
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
        `Failed to delete message ${uuid}: ${response.status()} - ${body}`,
      );
    }
  }

  // Service key methods (superuser only)

  async getServiceKeys(): Promise<ServiceKey[]> {
    const response = await this.request.get(
      `${API_URL}/api/v1/superuser/keys`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get service keys: ${response.status()} - ${body}`,
      );
    }

    const data: ServiceKeysResponse = await response.json();
    return data.keys || [];
  }

  async createServiceKey(
    service: string,
    name?: string,
    expiration?: number,
  ): Promise<ServiceKey> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/superuser/keys`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          service,
          name,
          expiration: expiration ?? null,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create service key: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async updateServiceKey(
    kid: string,
    updates: {name?: string; expiration?: number},
  ): Promise<ServiceKey> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/superuser/keys/${kid}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: updates,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to update service key ${kid}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async deleteServiceKey(kid: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/superuser/keys/${kid}`,
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
        `Failed to delete service key ${kid}: ${response.status()} - ${body}`,
      );
    }
  }

  // Quota methods

  async getOrganizationQuota(orgName: string): Promise<Quota[]> {
    const response = await this.request.get(
      `${API_URL}/api/v1/organization/${orgName}/quota`,
      {
        timeout: 5000,
      },
    );

    if (response.status() === 404) {
      return [];
    }

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get quota for ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async createOrganizationQuota(
    orgName: string,
    limitBytes: number,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/quota`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          limit_bytes: limitBytes,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create quota for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async updateOrganizationQuota(
    orgName: string,
    quotaId: string,
    limitBytes: number,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/organization/${orgName}/quota/${quotaId}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          limit_bytes: limitBytes,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to update quota for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async deleteOrganizationQuota(
    orgName: string,
    quotaId: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/quota/${quotaId}`,
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
        `Failed to delete quota for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async createQuotaLimit(
    orgName: string,
    quotaId: string,
    type: 'Warning' | 'Reject',
    thresholdPercent: number,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/quota/${quotaId}/limit`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          type,
          threshold_percent: thresholdPercent,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create quota limit for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async deleteQuotaLimit(
    orgName: string,
    quotaId: string,
    limitId: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/quota/${quotaId}/limit/${limitId}`,
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
        `Failed to delete quota limit for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Create a quota for a user namespace using superuser API.
   * This is different from organization quotas and requires superuser privileges.
   */
  async createUserQuotaSuperuser(
    namespace: string,
    limitBytes: number,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/superuser/users/${namespace}/quota`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          limit_bytes: limitBytes,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create quota for user ${namespace}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Get quotas for a user namespace using superuser API.
   */
  async getUserQuotaSuperuser(namespace: string): Promise<Quota[]> {
    const response = await this.request.get(
      `${API_URL}/api/v1/superuser/users/${namespace}/quota`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get quota for user ${namespace}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  /**
   * Delete a quota for a user namespace using superuser API.
   */
  async deleteUserQuotaSuperuser(
    namespace: string,
    quotaId: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/superuser/users/${namespace}/quota/${quotaId}`,
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
        `Failed to delete quota for user ${namespace}: ${response.status()} - ${body}`,
      );
    }
  }

  // Build methods

  /**
   * Start a Dockerfile build for a repository.
   * This creates a simple build from a Dockerfile content.
   */
  async startDockerfileBuild(
    namespace: string,
    repo: string,
    dockerfileContent = 'FROM scratch\n',
  ): Promise<{id: string}> {
    const token = await this.fetchToken();

    // Step 1: Get a file drop URL
    const fileDropResponse = await this.request.post(
      `${API_URL}/api/v1/filedrop/`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          mimeType: 'application/octet-stream',
        },
      },
    );

    if (!fileDropResponse.ok()) {
      const body = await fileDropResponse.text();
      throw new Error(
        `Failed to get file drop URL: ${fileDropResponse.status()} - ${body}`,
      );
    }

    const fileDropData = await fileDropResponse.json();
    const fileId = fileDropData.file_id;
    const uploadUrl = fileDropData.url;

    // Step 2: Upload the Dockerfile content
    const uploadResponse = await this.request.put(uploadUrl, {
      timeout: 10000,
      headers: {
        'Content-Type': 'application/octet-stream',
      },
      data: dockerfileContent,
    });

    if (!uploadResponse.ok()) {
      const body = await uploadResponse.text();
      throw new Error(
        `Failed to upload Dockerfile: ${uploadResponse.status()} - ${body}`,
      );
    }

    // Step 3: Start the build
    const buildResponse = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/build/`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          file_id: fileId,
        },
      },
    );

    if (!buildResponse.ok()) {
      const body = await buildResponse.text();
      throw new Error(
        `Failed to start build for ${namespace}/${repo}: ${buildResponse.status()} - ${body}`,
      );
    }

    return buildResponse.json();
  }

  // Proxy cache methods

  async getProxyCacheConfig(orgName: string): Promise<ProxyCacheConfig | null> {
    const response = await this.request.get(
      `${API_URL}/api/v1/organization/${orgName}/proxycache`,
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
        `Failed to get proxy cache config for ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async createProxyCacheConfig(
    orgName: string,
    config: ProxyCacheConfig,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/proxycache`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          org_name: orgName, // Required by the API endpoint
          upstream_registry: config.upstream_registry,
          expiration_s: config.expiration_s ?? 86400,
          insecure: config.insecure ?? false,
          upstream_registry_username: config.upstream_registry_username ?? null,
          upstream_registry_password: config.upstream_registry_password ?? null,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create proxy cache config for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async deleteProxyCacheConfig(orgName: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/proxycache`,
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
        `Failed to delete proxy cache config for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  // Tag management methods

  /**
   * Get tags for a repository.
   * Uses GET /api/v1/repository/{namespace}/{repo}/tag/
   */
  async getTags(
    namespace: string,
    repo: string,
    options?: {
      page?: number;
      limit?: number;
      onlyActiveTags?: boolean;
      specificTag?: string;
    },
  ): Promise<GetTagsResponse> {
    const params = new URLSearchParams();
    params.set('page', String(options?.page ?? 1));
    params.set('limit', String(options?.limit ?? 100));
    params.set('onlyActiveTags', String(options?.onlyActiveTags ?? true));
    if (options?.specificTag) {
      params.set('specificTag', options.specificTag);
    }

    const response = await this.request.get(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/tag/?${params.toString()}`,
      {
        timeout: 10000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get tags for ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  /**
   * Create or update a tag pointing to a manifest.
   * Uses PUT /api/v1/repository/{namespace}/{repo}/tag/{tag}
   */
  async createTag(
    namespace: string,
    repo: string,
    tag: string,
    manifestDigest: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/tag/${tag}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          manifest_digest: manifestDigest,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create tag ${tag} for ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Delete a tag (soft delete - can be restored within time machine window).
   * Uses DELETE /api/v1/repository/{namespace}/{repo}/tag/{tag}
   */
  async deleteTag(namespace: string, repo: string, tag: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/tag/${tag}`,
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
        `Failed to delete tag ${tag} from ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Set tag immutability.
   * Uses PUT /api/v1/repository/{namespace}/{repo}/tag/{tag}
   */
  async setTagImmutability(
    namespace: string,
    repo: string,
    tag: string,
    immutable: boolean,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/tag/${tag}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          immutable,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to set immutability for tag ${tag} in ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Set tag expiration.
   * Uses PUT /api/v1/repository/{namespace}/{repo}/tag/{tag}
   * @param expiration Unix timestamp in seconds, or null to clear expiration
   */
  async setTagExpiration(
    namespace: string,
    repo: string,
    tag: string,
    expiration: number | null,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/tag/${tag}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: {
          expiration,
        },
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to set expiration for tag ${tag} in ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  // Immutability policy methods

  /**
   * Get immutability policies for an organization.
   */
  async getOrgImmutabilityPolicies(
    orgName: string,
  ): Promise<{policies: ImmutabilityPolicy[]}> {
    const response = await this.request.get(
      `${API_URL}/api/v1/organization/${orgName}/immutabilitypolicy/`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get immutability policies for ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  /**
   * Create an immutability policy for an organization.
   */
  async createOrgImmutabilityPolicy(
    orgName: string,
    policy: Omit<ImmutabilityPolicy, 'uuid'>,
  ): Promise<{uuid: string}> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/immutabilitypolicy/`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: policy,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create immutability policy for ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  /**
   * Update an immutability policy for an organization.
   */
  async updateOrgImmutabilityPolicy(
    orgName: string,
    policyUuid: string,
    policy: Omit<ImmutabilityPolicy, 'uuid'>,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/organization/${orgName}/immutabilitypolicy/${policyUuid}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: policy,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to update immutability policy ${policyUuid} for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Delete an immutability policy for an organization.
   */
  async deleteOrgImmutabilityPolicy(
    orgName: string,
    policyUuid: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/immutabilitypolicy/${policyUuid}`,
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
        `Failed to delete immutability policy ${policyUuid} from ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Get immutability policies for a repository.
   */
  async getRepoImmutabilityPolicies(
    namespace: string,
    repo: string,
  ): Promise<{policies: ImmutabilityPolicy[]}> {
    const response = await this.request.get(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/immutabilitypolicy/`,
      {
        timeout: 5000,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to get immutability policies for ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  /**
   * Create an immutability policy for a repository.
   */
  async createRepoImmutabilityPolicy(
    namespace: string,
    repo: string,
    policy: Omit<ImmutabilityPolicy, 'uuid'>,
  ): Promise<{uuid: string}> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/immutabilitypolicy/`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: policy,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create immutability policy for ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  /**
   * Update an immutability policy for a repository.
   */
  async updateRepoImmutabilityPolicy(
    namespace: string,
    repo: string,
    policyUuid: string,
    policy: Omit<ImmutabilityPolicy, 'uuid'>,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/immutabilitypolicy/${policyUuid}`,
      {
        timeout: 5000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: policy,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to update immutability policy ${policyUuid} for ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  /**
   * Delete an immutability policy for a repository.
   */
  async deleteRepoImmutabilityPolicy(
    namespace: string,
    repo: string,
    policyUuid: string,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/repository/${namespace}/${repo}/immutabilitypolicy/${policyUuid}`,
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
        `Failed to delete immutability policy ${policyUuid} from ${namespace}/${repo}: ${response.status()} - ${body}`,
      );
    }
  }

  // Organization mirror methods

  async createOrgMirrorConfig(
    orgName: string,
    config: OrgMirrorConfig,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/mirror`,
      {
        timeout: 10000,
        headers: {
          'X-CSRF-Token': token,
        },
        data: config,
      },
    );

    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to create org mirror config for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async getOrgMirrorConfig(
    orgName: string,
  ): Promise<OrgMirrorConfigResponse | null> {
    const response = await this.request.get(
      `${API_URL}/api/v1/organization/${orgName}/mirror`,
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
        `Failed to get org mirror config for ${orgName}: ${response.status()} - ${body}`,
      );
    }

    return response.json();
  }

  async updateOrgMirrorConfig(
    orgName: string,
    updates: Partial<OrgMirrorConfig>,
  ): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.put(
      `${API_URL}/api/v1/organization/${orgName}/mirror`,
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
        `Failed to update org mirror config for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async deleteOrgMirrorConfig(orgName: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.delete(
      `${API_URL}/api/v1/organization/${orgName}/mirror`,
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
        `Failed to delete org mirror config for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async triggerOrgMirrorSync(orgName: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/mirror/sync-now`,
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
        `Failed to trigger org mirror sync for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }

  async cancelOrgMirrorSync(orgName: string): Promise<void> {
    const token = await this.fetchToken();
    const response = await this.request.post(
      `${API_URL}/api/v1/organization/${orgName}/mirror/sync-cancel`,
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
        `Failed to cancel org mirror sync for ${orgName}: ${response.status()} - ${body}`,
      );
    }
  }
}
