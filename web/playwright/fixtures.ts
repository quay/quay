/**
 * Playwright Custom Fixtures
 *
 * Provides pre-authenticated contexts for different user roles.
 * Tests can extend these fixtures to get logged-in sessions.
 *
 * @example
 * ```typescript
 * import { test, expect } from '../fixtures';
 *
 * test('can view organization', async ({ authenticatedPage }) => {
 *   await authenticatedPage.goto('/organization');
 *   await expect(authenticatedPage.getByText('Organizations')).toBeVisible();
 * });
 *
 * test('superuser can manage users', async ({ superuserPage }) => {
 *   await superuserPage.goto('/superuser');
 *   await expect(superuserPage.getByText('Users')).toBeVisible();
 * });
 * ```
 */

import {
  test as base,
  expect,
  Page,
  APIRequestContext,
  BrowserContext,
} from '@playwright/test';
import {TEST_USERS} from './global-setup';
import {API_URL} from './utils/config';
import {
  ApiClient,
  PrototypeRole,
  RepositoryVisibility,
  TeamRole,
} from './utils/api';

// ============================================================================
// TestApi: Auto-cleanup API client for tests
// ============================================================================

/**
 * Cleanup action to run after test completes
 */
type CleanupAction = () => Promise<void>;

/**
 * Created organization info
 */
export interface CreatedOrg {
  name: string;
  email: string;
}

/**
 * Created repository info
 */
export interface CreatedRepo {
  namespace: string;
  name: string;
  fullName: string;
}

/**
 * Created team info
 */
export interface CreatedTeam {
  orgName: string;
  name: string;
}

/**
 * Created robot info
 */
export interface CreatedRobot {
  orgName: string;
  shortname: string;
  fullName: string;
}

/**
 * Created quota info
 */
export interface CreatedQuota {
  orgName: string;
  quotaId: string;
  limitBytes: number;
}

/**
 * Created message info
 */
export interface CreatedMessage {
  uuid: string;
  content: string;
  severity: 'info' | 'warning' | 'error';
}

/**
 * API client with auto-cleanup tracking.
 *
 * All resources created via this client are automatically
 * cleaned up when the test completes (even on failure).
 *
 * @example
 * ```typescript
 * test('my test', async ({api}) => {
 *   const org = await api.organization();
 *   const repo = await api.repository(org.name);
 *   // After test: auto-deletes repo, then org (reverse order)
 * });
 * ```
 */
export class TestApi {
  private client: ApiClient;
  private cleanupStack: CleanupAction[] = [];

  constructor(client: ApiClient) {
    this.client = client;
  }

  /**
   * Access the underlying ApiClient for operations
   * that don't need auto-cleanup tracking
   */
  get raw(): ApiClient {
    return this.client;
  }

  /**
   * Create a unique organization.
   * Automatically deleted after test.
   */
  async organization(namePrefix = 'org'): Promise<CreatedOrg> {
    const name = uniqueName(namePrefix);
    const email = `${name}@example.com`;

    await this.client.createOrganization(name, email);

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteOrganization(name);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {name, email};
  }

  /**
   * Create a unique repository.
   * Automatically deleted after test.
   *
   * @param namespace - Organization or username (defaults to test user)
   */
  async repository(
    namespace?: string,
    namePrefix = 'repo',
    visibility: RepositoryVisibility = 'private',
  ): Promise<CreatedRepo> {
    const ns = namespace ?? TEST_USERS.user.username;
    const name = uniqueName(namePrefix);

    await this.client.createRepository(ns, name, visibility);

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteRepository(ns, name);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {
      namespace: ns,
      name,
      fullName: `${ns}/${name}`,
    };
  }

  /**
   * Create a repository with an exact name (supports multi-segment names like "release/installer").
   * Automatically deleted after test.
   *
   * @param namespace - Organization or username
   * @param name - Exact repository name (can contain "/" for multi-segment)
   * @param visibility - Repository visibility (default: private)
   *
   * @example
   * ```typescript
   * // Create a multi-segment repository
   * const repo = await api.repositoryWithName('myorg', 'release/installer');
   * ```
   */
  async repositoryWithName(
    namespace: string,
    name: string,
    visibility: RepositoryVisibility = 'private',
  ): Promise<CreatedRepo> {
    await this.client.createRepository(namespace, name, visibility);

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteRepository(namespace, name);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {
      namespace,
      name,
      fullName: `${namespace}/${name}`,
    };
  }

  /**
   * Create a team in an organization.
   * Automatically deleted after test.
   */
  async team(
    orgName: string,
    namePrefix = 'team',
    role: TeamRole = 'member',
  ): Promise<CreatedTeam> {
    const name = uniqueName(namePrefix);

    await this.client.createTeam(orgName, name, role);

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteTeam(orgName, name);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {orgName, name};
  }

  /**
   * Create a robot account in an organization.
   * Automatically deleted after test.
   */
  async robot(
    orgName: string,
    namePrefix = 'bot',
    description = '',
  ): Promise<CreatedRobot> {
    // Robot names can't have dashes, only underscores
    const shortname = uniqueName(namePrefix).replace(/-/g, '_');

    await this.client.createRobot(orgName, shortname, description);

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteRobot(orgName, shortname);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {
      orgName,
      shortname,
      fullName: `${orgName}+${shortname}`,
    };
  }

  /**
   * Set repository to MIRROR state.
   * (No cleanup needed - deleting repo handles it)
   */
  async setMirrorState(namespace: string, repoName: string): Promise<void> {
    await this.client.changeRepositoryState(namespace, repoName, 'MIRROR');
  }

  /**
   * Add a member to a team (for test setup).
   * Automatically removed after test.
   *
   * Note: If the team or org is deleted, this cleanup becomes a no-op.
   */
  async teamMember(
    orgName: string,
    teamName: string,
    memberName: string,
  ): Promise<void> {
    await this.client.addTeamMember(orgName, teamName, memberName);

    this.cleanupStack.push(async () => {
      try {
        await this.client.removeTeamMember(orgName, teamName, memberName);
      } catch {
        /* ignore cleanup errors - member may already be removed or team deleted */
      }
    });
  }

  /**
   * Create a default permission (prototype).
   * Automatically deleted after test.
   */
  async prototype(
    orgName: string,
    role: PrototypeRole,
    delegate: {name: string; kind: 'user' | 'team'},
    activatingUser?: {name: string},
  ): Promise<{id: string}> {
    const result = await this.client.createPrototype(
      orgName,
      role,
      delegate,
      activatingUser,
    );

    this.cleanupStack.push(async () => {
      try {
        await this.client.deletePrototype(orgName, result.id);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return result;
  }

  /**
   * Add a permission to a repository.
   * Automatically deleted after test.
   *
   * @param namespace - Organization or username that owns the repository
   * @param repoName - Repository name
   * @param entityType - Type of entity ('user' for users/robots, 'team' for teams)
   * @param entityName - Name of the entity (username, robot fullName like "org+bot", or team name)
   * @param role - Permission level ('read', 'write', or 'admin')
   */
  async repositoryPermission(
    namespace: string,
    repoName: string,
    entityType: 'user' | 'team',
    entityName: string,
    role: PrototypeRole = 'read',
  ): Promise<{
    namespace: string;
    repoName: string;
    entityType: 'user' | 'team';
    entityName: string;
  }> {
    await this.client.addRepositoryPermission(
      namespace,
      repoName,
      entityType,
      entityName,
      role,
    );

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteRepositoryPermission(
          namespace,
          repoName,
          entityType,
          entityName,
        );
      } catch {
        /* ignore cleanup errors - permission may already be deleted */
      }
    });

    return {namespace, repoName, entityType, entityName};
  }

  /**
   * Create a notification for a repository.
   * Automatically deleted after test.
   */
  async notification(
    namespace: string,
    repoName: string,
    event: string,
    method: string,
    config: Record<string, unknown>,
    title?: string,
  ): Promise<{uuid: string; namespace: string; repoName: string}> {
    const result = await this.client.createRepositoryNotification(
      namespace,
      repoName,
      event,
      method,
      config,
      {},
      title,
    );

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteRepositoryNotification(
          namespace,
          repoName,
          result.uuid,
        );
      } catch {
        /* ignore cleanup errors - notification may already be deleted */
      }
    });

    return {uuid: result.uuid, namespace, repoName};
  }

  /**
   * Create a quota for an organization.
   * Automatically deleted after test.
   *
   * @param orgName - Organization name
   * @param limitBytes - Quota limit in bytes (default: 10 GiB)
   */
  async quota(
    orgName: string,
    limitBytes = 10737418240, // 10 GiB default
  ): Promise<CreatedQuota> {
    await this.client.createOrganizationQuota(orgName, limitBytes);

    // Fetch quota to get the ID
    const quotas = await this.client.getOrganizationQuota(orgName);
    if (quotas.length === 0) {
      throw new Error(`Failed to create quota for ${orgName}`);
    }
    const quotaId = quotas[0].id;

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteOrganizationQuota(orgName, quotaId);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {orgName, quotaId, limitBytes};
  }

  /**
   * Create a global message.
   * Automatically deleted after test.
   * (Superuser only)
   */
  async message(
    content: string,
    severity: 'info' | 'warning' | 'error' = 'info',
  ): Promise<CreatedMessage> {
    const result = await this.client.createMessage(content, severity);

    this.cleanupStack.push(async () => {
      try {
        await this.client.deleteMessage(result.uuid);
      } catch {
        /* ignore cleanup errors */
      }
    });

    return {
      uuid: result.uuid,
      content: result.content,
      severity: result.severity,
    };
  }

  /**
   * Run all cleanup actions in reverse order.
   * Called automatically by fixture teardown.
   */
  async cleanup(): Promise<void> {
    // Run in reverse order (LIFO)
    let action = this.cleanupStack.pop();
    while (action) {
      await action();
      action = this.cleanupStack.pop();
    }
  }
}

// ============================================================================
// Quay Config Types
// ============================================================================

/**
 * Known Quay feature flags that can be enabled/disabled
 */
export type QuayFeature =
  | 'BILLING'
  | 'QUOTA_MANAGEMENT'
  | 'EDIT_QUOTA'
  | 'AUTO_PRUNE'
  | 'PROXY_CACHE'
  | 'REPO_MIRROR'
  | 'SECURITY_SCANNER'
  | 'CHANGE_TAG_EXPIRATION'
  | 'USER_METADATA'
  | 'MAILING'
  | 'IMAGE_EXPIRY_TRIGGER'
  | 'SUPERUSERS_FULL_ACCESS';

/**
 * Quay configuration from /config endpoint
 */
export interface QuayConfig {
  features: Partial<Record<QuayFeature, boolean>>;
  config: Record<string, unknown>;
}

/**
 * Helper to skip tests when required features are not enabled.
 * Returns a tuple that can be spread into test.skip()
 *
 * @example
 * ```typescript
 * test('requires billing', async ({ quayConfig }) => {
 *   test.skip(...skipUnlessFeature(quayConfig, 'BILLING'));
 *   // test code...
 * });
 *
 * test('requires multiple features', async ({ quayConfig }) => {
 *   test.skip(...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'));
 *   // test code...
 * });
 * ```
 */
export function skipUnlessFeature(
  config: QuayConfig | null,
  ...features: QuayFeature[]
): [boolean, string] {
  const missing = features.filter((f) => !config?.features?.[f]);
  if (missing.length === 0) return [false, ''];
  return [true, `Required feature(s) not enabled: ${missing.join(', ')}`];
}

/**
 * Login a user and return the API client (with cached CSRF token)
 */
async function loginUser(
  request: APIRequestContext,
  username: string,
  password: string,
): Promise<ApiClient> {
  const api = new ApiClient(request);
  await api.signIn(username, password);
  return api;
}

/**
 * Extended test fixtures providing authenticated contexts
 */
type TestFixtures = {
  // CSRF token for API calls (after login)
  csrfToken: string;

  // Pre-authenticated page as regular user
  authenticatedPage: Page;

  // Pre-authenticated page as superuser
  superuserPage: Page;

  // Pre-authenticated page as readonly user
  readonlyPage: Page;

  // Pre-authenticated API request context as regular user
  authenticatedRequest: APIRequestContext;

  // Pre-authenticated API request context as superuser
  superuserRequest: APIRequestContext;

  // Quay configuration (features, config settings)
  quayConfig: QuayConfig;

  // API client for regular user with auto-cleanup
  api: TestApi;

  // API client for superuser with auto-cleanup
  superuserApi: TestApi;

  // Auto-fixture: skips tests based on @feature: tags (runs automatically)
  _autoSkipByFeature: void;
};

/**
 * Worker fixtures (shared across tests in same worker)
 */
type WorkerFixtures = {
  // Browser context with regular user auth
  userContext: BrowserContext;

  // Browser context with superuser auth
  superuserContext: BrowserContext;

  // Browser context with readonly user auth
  readonlyContext: BrowserContext;

  // Cached Quay config (fetched once per worker)
  cachedQuayConfig: QuayConfig;
};

/**
 * Extended test with custom fixtures
 */
export const test = base.extend<TestFixtures, WorkerFixtures>({
  // =========================================================================
  // Worker-scoped fixtures (created once per worker)
  // =========================================================================

  userContext: [
    async ({browser}, use) => {
      const context = await browser.newContext();
      const request = context.request;

      // Login as regular user
      await loginUser(
        request,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await use(context);
      await context.close();
    },
    {scope: 'worker'},
  ],

  superuserContext: [
    async ({browser}, use) => {
      const context = await browser.newContext();
      const request = context.request;

      // Login as admin (superuser)
      await loginUser(
        request,
        TEST_USERS.admin.username,
        TEST_USERS.admin.password,
      );

      await use(context);
      await context.close();
    },
    {scope: 'worker'},
  ],

  readonlyContext: [
    async ({browser}, use) => {
      const context = await browser.newContext();
      const request = context.request;

      // Login as readonly user
      await loginUser(
        request,
        TEST_USERS.readonly.username,
        TEST_USERS.readonly.password,
      );

      await use(context);
      await context.close();
    },
    {scope: 'worker'},
  ],

  cachedQuayConfig: [
    async ({browser}, use) => {
      // Create a temporary context just to fetch config
      const context = await browser.newContext();
      const response = await context.request.get(`${API_URL}/config`);
      if (!response.ok()) {
        await context.close();
        throw new Error(`Failed to fetch Quay config: ${response.status()}`);
      }
      const config = (await response.json()) as QuayConfig;
      await context.close();
      await use(config);
    },
    {scope: 'worker'},
  ],

  // =========================================================================
  // Test-scoped fixtures (created fresh for each test)
  // =========================================================================

  csrfToken: async ({request}, use) => {
    const api = await loginUser(
      request,
      TEST_USERS.user.username,
      TEST_USERS.user.password,
    );
    const token = await api.getToken();
    await use(token);
  },

  authenticatedPage: async ({userContext}, use) => {
    const page = await userContext.newPage();
    await use(page);
    await page.close();
  },

  superuserPage: async ({superuserContext}, use) => {
    const page = await superuserContext.newPage();
    await use(page);
    await page.close();
  },

  readonlyPage: async ({readonlyContext}, use) => {
    const page = await readonlyContext.newPage();
    await use(page);
    await page.close();
  },

  authenticatedRequest: async ({userContext}, use) => {
    await use(userContext.request);
  },

  superuserRequest: async ({superuserContext}, use) => {
    await use(superuserContext.request);
  },

  quayConfig: async ({cachedQuayConfig}, use) => {
    await use(cachedQuayConfig);
  },

  api: async ({authenticatedRequest}, use) => {
    const client = new ApiClient(authenticatedRequest);
    const testApi = new TestApi(client);
    await use(testApi);
    await testApi.cleanup();
  },

  superuserApi: async ({superuserRequest}, use) => {
    const client = new ApiClient(superuserRequest);
    const testApi = new TestApi(client);
    await use(testApi);
    await testApi.cleanup();
  },

  // =========================================================================
  // Auto-fixture: Skip tests based on @feature: tags
  // =========================================================================

  /**
   * Automatically skip tests that have @feature:X tags when those
   * features are not enabled in Quay config.
   *
   * This eliminates the need for manual `test.skip(...skipUnlessFeature(...))`
   * calls in each test. Just add the tag to the describe block:
   *
   * @example
   * ```typescript
   * test.describe('Repository Mirroring', {tag: ['@feature:REPO_MIRROR']}, () => {
   *   test('creates mirror', async ({authenticatedPage}) => {
   *     // Auto-skipped if REPO_MIRROR is not enabled - no manual skip needed!
   *   });
   * });
   * ```
   */
  _autoSkipByFeature: [
    async ({quayConfig}, use, testInfo) => {
      // Extract feature names from @feature:X tags
      const featureTags = testInfo.tags
        .filter((tag) => tag.startsWith('@feature:'))
        .map((tag) => tag.replace('@feature:', '') as QuayFeature);

      if (featureTags.length > 0) {
        const [shouldSkip, reason] = skipUnlessFeature(
          quayConfig,
          ...featureTags,
        );
        testInfo.skip(shouldSkip, reason);
      }

      await use();
    },
    {auto: true},
  ],
});

// Re-export expect for convenience
export {expect};

/**
 * Utility to generate unique names for test resources
 */
export function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random()
    .toString(36)
    .substring(2, 8)}`;
}
