import {test, expect} from '../../fixtures';

test.describe(
  'Repository Builds',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    // Real builds take time — extend timeout for all tests in this describe
    test.setTimeout(180_000);

    test('triggered build appears in builds list', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('builds');
      const repo = await api.repository(org.name, 'build-list');

      // Trigger a build
      const build = await api.build(org.name, repo.name);

      // Navigate to Builds tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      // The build ID should appear in the table
      await expect(
        authenticatedPage.getByText(build.buildId.substring(0, 8)),
      ).toBeVisible();
    });

    test('build completes successfully', async ({api}) => {
      const org = await api.organization('buildcomplete');
      const repo = await api.repository(org.name, 'build-success');

      // Trigger a build with a simple Dockerfile
      const build = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL test="e2e-build"\n',
      );

      // Wait for build to reach a terminal phase
      const result = await api.raw.waitForBuildPhase(
        org.name,
        repo.name,
        build.buildId,
      );

      expect(result.phase).toBe('complete');
    });

    test('build creates expected tag in repository', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('buildtag');
      const repo = await api.repository(org.name, 'build-tags');
      const tagName = 'e2e-test';

      // Trigger a build with a specific tag
      const build = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL test="e2e-tag"\n',
        [tagName],
      );

      // Wait for build to complete
      const result = await api.raw.waitForBuildPhase(
        org.name,
        repo.name,
        build.buildId,
      );
      expect(result.phase).toBe('complete');

      // Navigate to Tags tab and verify the tag exists
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=tags`,
      );

      await expect(authenticatedPage.getByText(tagName)).toBeVisible();
    });

    test('build logs are visible', async ({authenticatedPage, api}) => {
      const org = await api.organization('buildlogs');
      const repo = await api.repository(org.name, 'build-logs');

      // Trigger a build
      const build = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL test="e2e-logs"\n',
      );

      // Wait for build to complete (or at least start building)
      await api.raw.waitForBuildPhase(org.name, repo.name, build.buildId);

      // Navigate to the build detail page
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
      );

      // Build logs page should show some content
      await expect(
        authenticatedPage
          .locator('[data-testid="build-logs"]')
          .or(authenticatedPage.getByText('Build Logs')),
      ).toBeVisible();
    });

    test('build detail page shows phases and supports expand/collapse', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldphases');
      const repo = await api.repository(org.name, 'phases-repo');

      const build = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL test="phases"\n',
      );

      await api.raw.waitForBuildPhase(org.name, repo.name, build.buildId);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
      );

      // Phase headers should be visible
      await expect(
        authenticatedPage.locator('.log-header').first(),
      ).toBeVisible();

      // Click a phase header to expand it
      const firstPhase = authenticatedPage.locator('.log-header').first();
      await firstPhase.click();

      // Download button should exist with correct link
      await expect(authenticatedPage.locator('#download-button')).toBeVisible();

      // Timestamps toggle should work
      await expect(
        authenticatedPage.locator('#toggle-timestamps-button'),
      ).toBeVisible();
      await authenticatedPage.locator('#toggle-timestamps-button').click();
      await authenticatedPage.locator('#toggle-timestamps-button').click();
    });

    test('build list sorts by date started', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldsort');
      const repo = await api.repository(org.name, 'sort-repo');

      const build1 = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL sort="first"\n',
      );
      await api.raw.waitForBuildPhase(org.name, repo.name, build1.buildId);

      const build2 = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL sort="second"\n',
      );
      await api.raw.waitForBuildPhase(org.name, repo.name, build2.buildId);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      // Both builds should appear in the table
      await expect(
        authenticatedPage.getByText(build1.buildId.substring(0, 8)),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(build2.buildId.substring(0, 8)),
      ).toBeVisible();

      // Default sort direction should be descending on "Date started"
      const dateHeader = authenticatedPage.getByRole('columnheader', {
        name: 'Date started',
      });
      await expect(dateHeader).toHaveAttribute('aria-sort', 'descending');

      // Click the sort button inside the header to toggle direction
      await dateHeader.getByRole('button').click();
      await expect(dateHeader).toHaveAttribute('aria-sort', 'ascending');

      // Both builds should remain visible after sort toggle
      await expect(
        authenticatedPage.getByText(build1.buildId.substring(0, 8)),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(build2.buildId.substring(0, 8)),
      ).toBeVisible();
    });

    test('shows empty state when no builds exist', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nobuilds');
      const repo = await api.repository(org.name, 'empty-builds');

      // Navigate to Builds tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      // Should show empty state
      await expect(
        authenticatedPage.getByText('No matching builds found'),
      ).toBeVisible();
    });
  },
);

test.describe(
  'Custom Git Trigger CRUD',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    test('custom git trigger lifecycle: create, verify, disable, enable, delete', async ({
      authenticatedPage,
      api,
    }) => {
      test.setTimeout(60_000);

      const org = await api.organization('trigcrud');
      const repo = await api.repository(org.name, 'trigger-crud');

      // Create and activate a custom git trigger via API
      const triggerUuid = await api.raw.createCustomGitTrigger(
        org.name,
        repo.name,
      );
      await api.raw.activateTrigger(org.name, repo.name, triggerUuid, {
        build_source: 'https://github.com/quay/quay',
      });

      // Verify trigger appears in the UI
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );
      await expect(
        authenticatedPage.getByText('https://github.com/quay/quay'),
      ).toBeVisible();

      // Disable trigger via API, verify UI shows disabled state
      await api.raw.toggleTrigger(org.name, repo.name, triggerUuid, false);
      await authenticatedPage.reload();
      await expect(
        authenticatedPage.getByText(/build trigger is user disabled/i),
      ).toBeVisible();

      // Re-enable trigger via API, verify disabled warning gone
      await api.raw.toggleTrigger(org.name, repo.name, triggerUuid, true);
      await authenticatedPage.reload();
      await expect(
        authenticatedPage.getByText(/build trigger is user disabled/i),
      ).not.toBeVisible();

      // Delete trigger via API, verify removed from UI
      await api.raw.deleteTrigger(org.name, repo.name, triggerUuid);
      await authenticatedPage.reload();
      await expect(
        authenticatedPage.getByText('https://github.com/quay/quay'),
      ).not.toBeVisible();
    });
  },
);

test.describe(
  'Build Triggers (mocked)',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    const mockTriggers = {
      triggers: [
        {
          id: 'github-trigger-uuid',
          service: 'github',
          is_active: true,
          build_source: 'myorg/myrepo',
          repository_url: 'https://github.com/myorg/myrepo',
          config: {
            build_source: 'myorg/myrepo',
            dockerfile_path: '/Dockerfile',
            context: '/',
            branchtag_regex: '^main$',
            default_tag_from_ref: true,
            latest_for_default_branch: true,
            tag_templates: ['${commit_info.short_sha}'],
            credentials: [
              {name: 'SSH Public Key', value: 'ssh-rsa AAAA-mock-key'},
            ],
          },
          can_invoke: true,
          enabled: true,
        },
        {
          id: 'gitlab-trigger-uuid',
          service: 'gitlab',
          is_active: true,
          build_source: 'gitlabns/gitlabrepo',
          repository_url: 'https://gitlab.com/gitlabns/gitlabrepo',
          config: {
            build_source: 'gitlabns/gitlabrepo',
            dockerfile_path: '/app/Dockerfile',
            context: '/app',
            default_tag_from_ref: false,
            latest_for_default_branch: false,
            tag_templates: [],
            credentials: [
              {name: 'SSH Public Key', value: 'ssh-rsa BBBB-mock-key'},
            ],
          },
          can_invoke: true,
          enabled: true,
        },
      ],
    };

    test('displays GitHub and GitLab triggers from mocked data', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('mocktrig');
      const repo = await api.repository(org.name, 'mock-triggers');

      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockTriggers),
          });
        },
      );

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await expect(
        authenticatedPage.getByText('push to GitHub repository'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('push to GitLab repository'),
      ).toBeVisible();
    });

    test('view trigger credentials modal shows SSH public key', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('mockcred');
      const repo = await api.repository(org.name, 'mock-creds');

      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockTriggers),
          });
        },
      );

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      // Open kebab menu on the first trigger row and click View Credentials
      await authenticatedPage
        .getByTestId('build-trigger-actions-kebab')
        .first()
        .click();
      await authenticatedPage.getByText('View Credentials').click();

      await expect(
        authenticatedPage.getByText('Trigger Credentials'),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('SSH Public Key')).toBeVisible();

      await authenticatedPage.getByRole('button', {name: 'Done'}).click();
    });
  },
);

test.describe(
  'Build Trigger Setup Wizards (mocked)',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    const triggerUuid = 'github01-0001-4c69-a5cc-ec372d0117cd';
    const gitlabTriggerUuid = 'gitlab01-0001-4c69-a5cc-ec372d0117cd';

    const refsFixture = {
      values: [
        {kind: 'branch', name: 'master'},
        {kind: 'branch', name: 'development'},
        {kind: 'tag', name: '1.0.0'},
        {kind: 'tag', name: '1.0.1'},
      ],
    };

    const subdirsFixture = {
      dockerfile_paths: [
        '/Dockerfile',
        '/dir1/Dockerfile',
        '/dir2/subdir2/nesteddir1/Dockerfile',
        '/dir2/subrdir1/Dockerfile',
      ],
      contextMap: {
        '/Dockerfile': ['/'],
        '/dir1/Dockerfile': ['/', '/dir1'],
        '/dir2/subrdir1/Dockerfile': ['/dir2', '/', '/dir2/subrdir1'],
        '/dir2/subdir2/nesteddir1/Dockerfile': [
          '/dir2/subdir2',
          '/',
          '/dir2/subdir2/nesteddir1',
          '/dir2',
        ],
      },
      status: 'success',
    };

    const analyzeFixture = {
      namespace: 'githuborg1',
      name: null,
      robots: [
        {
          name: 'githuborg1+robot1',
          kind: 'user',
          is_robot: true,
          can_read: false,
        },
        {
          name: 'githuborg1+robot2',
          kind: 'user',
          is_robot: true,
          can_read: false,
        },
      ],
      status: 'publicbase',
      message: null,
      is_admin: true,
    };

    test('creates GitHub build trigger via wizard', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('ghwiz');
      const repo = await api.repository(org.name, 'gh-trigger');

      // Mock all wizard endpoints
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}`,
        async (route) => {
          if (route.request().method() === 'GET') {
            await route.fulfill({
              json: {
                id: triggerUuid,
                service: 'github',
                is_active: false,
                config: {},
                enabled: true,
              },
            });
          } else {
            await route.continue();
          }
        },
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}/namespaces`,
        async (route) => {
          await route.fulfill({
            json: {
              namespaces: [
                {
                  personal: true,
                  id: 'githuborg1',
                  title: 'Org 1',
                  avatar_url:
                    'https://avatars.githubusercontent.com/u/1234567?v=3',
                  url: 'https://github.com/githuborg1',
                  score: 0,
                },
                {
                  personal: true,
                  id: 'githuborg2',
                  title: 'Org 2',
                  avatar_url:
                    'https://avatars.githubusercontent.com/u/1234567?v=3',
                  url: 'https://github.com/githuborg2',
                  score: 50,
                },
              ],
            },
          });
        },
      );

      const now = Math.floor(Date.now() / 1000);
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}/sources`,
        async (route) => {
          await route.fulfill({
            json: {
              sources: [
                {
                  name: 'repo1',
                  full_name: 'githuborg1/repo1',
                  description: 'repo1 description',
                  last_updated: now,
                  has_admin_permissions: true,
                  private: false,
                },
                {
                  name: 'repo2',
                  full_name: 'githuborg1/repo2',
                  description: 'repo2 description',
                  last_updated: now,
                  has_admin_permissions: true,
                  private: false,
                },
              ],
            },
          });
        },
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}/fields/refs`,
        async (route) => route.fulfill({json: refsFixture}),
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}/subdir`,
        async (route) => route.fulfill({json: subdirsFixture}),
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}/analyze`,
        async (route) => route.fulfill({json: analyzeFixture}),
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${triggerUuid}/activate`,
        async (route) => {
          await route.fulfill({
            json: {
              id: triggerUuid,
              service: 'github',
              is_active: true,
              config: {
                credentials: [{name: 'SSH Public Key', value: 'ssh-rsa AAAA'}],
              },
            },
          });
        },
      );

      // Navigate to the setup wizard
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/trigger/${triggerUuid}`,
      );

      // Step 1: Select organization
      await expect(authenticatedPage.getByText('Org 1')).toBeVisible();
      await authenticatedPage.locator('#githuborg1-checkbox').click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 2: Select repository
      await expect(
        authenticatedPage.getByText('repo1', {exact: true}),
      ).toBeVisible();
      await authenticatedPage.locator('#repo1-checkbox').click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 3: Trigger options (branch filter)
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 4: Tagging options
      await authenticatedPage
        .locator('#tag-manifest-with-branch-or-tag-name-checkbox')
        .click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 5: Dockerfile path — click typeahead, select from dropdown
      await authenticatedPage
        .locator('input[aria-label="Type to filter"]')
        .click();
      await authenticatedPage
        .getByRole('option', {name: '/Dockerfile'})
        .first()
        .click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 6: Context path — click typeahead, select from dropdown
      await authenticatedPage
        .locator('input[aria-label="Type to filter"]')
        .click();
      await authenticatedPage.getByRole('option', {name: '/'}).first().click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 7: Robot account (skip)
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 8: Review and submit
      await authenticatedPage.locator('button[type="submit"]').click();

      // Confirmation
      await expect(
        authenticatedPage.getByText('Trigger has been successfully activated'),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('SSH Public Key')).toBeVisible();
    });

    test('creates GitLab build trigger via wizard', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('glwiz');
      const repo = await api.repository(org.name, 'gl-trigger');

      // Mock all wizard endpoints
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}`,
        async (route) => {
          if (route.request().method() === 'GET') {
            await route.fulfill({
              json: {
                id: gitlabTriggerUuid,
                service: 'gitlab',
                is_active: false,
                config: {},
                enabled: true,
              },
            });
          } else {
            await route.continue();
          }
        },
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}/namespaces`,
        async (route) => {
          await route.fulfill({
            json: {
              namespaces: [
                {
                  personal: true,
                  id: 'gitlabuser1',
                  title: 'User 1',
                  avatar_url: null,
                  url: 'https://gitlab.com/gitlabuser1',
                  score: 0,
                },
                {
                  personal: true,
                  id: 'gitlabgroup2',
                  title: 'Group 2',
                  avatar_url: null,
                  url: 'https://gitlab.com/groups/gitlabgroup2',
                  score: 50,
                },
              ],
            },
          });
        },
      );

      const now = Math.floor(Date.now() / 1000);
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}/sources`,
        async (route) => {
          await route.fulfill({
            json: {
              sources: [
                {
                  name: 'repo1',
                  full_name: 'gitlabgroup2/repo1',
                  description: 'repo1 description',
                  last_updated: now,
                  has_admin_permissions: true,
                  private: false,
                },
              ],
            },
          });
        },
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}/fields/refs`,
        async (route) => route.fulfill({json: refsFixture}),
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}/subdir`,
        async (route) => route.fulfill({json: subdirsFixture}),
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}/analyze`,
        async (route) => route.fulfill({json: analyzeFixture}),
      );
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}/activate`,
        async (route) => {
          await route.fulfill({
            json: {
              id: gitlabTriggerUuid,
              service: 'gitlab',
              is_active: true,
              config: {
                credentials: [{name: 'SSH Public Key', value: 'ssh-rsa BBBB'}],
              },
            },
          });
        },
      );

      // Navigate to the setup wizard
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/trigger/${gitlabTriggerUuid}`,
      );

      // Step 1: Select organization
      await expect(authenticatedPage.getByText('Group 2')).toBeVisible();
      await authenticatedPage.locator('#gitlabgroup2-checkbox').click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 2: Select repository
      await expect(
        authenticatedPage.getByText('repo1', {exact: true}),
      ).toBeVisible();
      await authenticatedPage.locator('#repo1-checkbox').click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 3: Trigger options
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 4: Tagging options
      await authenticatedPage
        .locator('#tag-manifest-with-branch-or-tag-name-checkbox')
        .click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 5: Dockerfile path — click typeahead, select from dropdown
      await authenticatedPage
        .locator('input[aria-label="Type to filter"]')
        .click();
      await authenticatedPage
        .getByRole('option', {name: '/Dockerfile'})
        .first()
        .click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 6: Context path — click typeahead, select from dropdown
      await authenticatedPage
        .locator('input[aria-label="Type to filter"]')
        .click();
      await authenticatedPage.getByRole('option', {name: '/'}).first().click();
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 7: Robot account (skip)
      await authenticatedPage
        .getByRole('button', {name: 'Next', exact: true})
        .click();

      // Step 8: Review and submit
      await authenticatedPage.locator('button[type="submit"]').click();

      // Confirmation
      await expect(
        authenticatedPage.getByText('Trigger has been successfully activated'),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('SSH Public Key')).toBeVisible();
    });
  },
);

test.describe('Repository Builds Tab Visibility', {tag: '@repository'}, () => {
  test(
    'Builds tab not visible for mirror repositories',
    {tag: '@feature:REPO_MIRROR'},
    async ({authenticatedPage, api}) => {
      const org = await api.organization('mirror');
      const repo = await api.repository(org.name, 'mirror-repo');

      // Set repository to MIRROR state
      await api.setMirrorState(org.name, repo.name);

      // Navigate to repository page
      await authenticatedPage.goto(`/repository/${org.name}/${repo.name}`);

      // Builds tab should not be visible
      await expect(authenticatedPage.getByText('Builds')).not.toBeVisible();
    },
  );

  test('Builds tab not visible for read-only repositories', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('readonly');
    const repo = await api.repository(org.name, 'readonly-repo');

    // Set repository to READ_ONLY state
    await api.raw.changeRepositoryState(org.name, repo.name, 'READ_ONLY');

    // Navigate to repository page
    await authenticatedPage.goto(`/repository/${org.name}/${repo.name}`);

    // Builds tab should not be visible
    await expect(authenticatedPage.getByText('Builds')).not.toBeVisible();
  });
});
