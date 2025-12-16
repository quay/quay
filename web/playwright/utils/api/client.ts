/**
 * API client for Playwright e2e tests
 *
 * Provides API interactions with CSRF token caching to reduce redundant requests.
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';

export type RepositoryVisibility = 'public' | 'private';
export type TeamRole = 'member' | 'creator' | 'admin';

export interface CreateUserResponse {
  username: string;
  awaiting_verification?: boolean;
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
}
