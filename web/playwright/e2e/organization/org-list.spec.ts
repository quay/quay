import {test, expect, uniqueName, skipUnlessFeature} from '../../fixtures';
import {createOrganization, deleteOrganization} from '../../utils/api';
import {TEST_USERS} from '../../global-setup';

test.describe('Organization List', {tag: ['@organization']}, () => {
  test(
    'org CRUD lifecycle: create, verify, duplicate error, delete',
    {tag: ['@critical', '@PROJQUAY-9948']},
    async ({authenticatedPage}) => {
      const orgName = uniqueName('crudtest');
      const orgEmail = `${orgName}@test.com`;

      await authenticatedPage.goto('/organization');

      // CREATE: Open modal, fill form, submit
      await authenticatedPage.locator('#create-organization-button').click();
      await authenticatedPage.locator('#create-org-name-input').fill(orgName);
      await authenticatedPage.locator('#create-org-email-input').fill(orgEmail);
      await authenticatedPage.locator('#create-org-confirm').click();

      // Verify success toast
      await expect(
        authenticatedPage.getByText(
          `Successfully created organization ${orgName}`,
        ),
      ).toBeVisible();

      // DUPLICATE ERROR: Try to create same org again
      await authenticatedPage.locator('#create-organization-button').click();
      await authenticatedPage.locator('#create-org-name-input').fill(orgName);
      await authenticatedPage
        .locator('#create-org-email-input')
        .fill('another@test.com');
      await authenticatedPage.locator('#create-org-confirm').click();

      // Verify error shown, modal still open
      await expect(
        authenticatedPage.getByText(
          'A user or organization with this name already exists',
        ),
      ).toBeVisible();
      await expect(
        authenticatedPage.locator('#create-org-cancel'),
      ).toBeVisible();
      await authenticatedPage.locator('#create-org-cancel').click();

      // DELETE: Search and bulk delete
      await authenticatedPage.locator('#orgslist-search-input').fill(orgName);
      await authenticatedPage.locator('#toolbar-dropdown-checkbox').click();
      await authenticatedPage.getByText('Select page').click();
      await authenticatedPage.getByRole('button', {name: 'Actions'}).click();
      await authenticatedPage.getByText('Delete').click();
      await authenticatedPage
        .locator('#delete-confirmation-input')
        .fill('confirm');
      await authenticatedPage
        .locator('#bulk-delete-modal')
        .getByRole('button', {name: 'Delete'})
        .click();

      // Verify deleted
      await expect(authenticatedPage.getByText('0 - 0 of 0')).toBeVisible();
    },
  );

  test.describe('search and filter', () => {
    let org1: string, org2: string;

    test.beforeEach(async ({authenticatedRequest}) => {
      org1 = uniqueName('searchtest');
      org2 = uniqueName('another');
      await createOrganization(authenticatedRequest, org1);
      await createOrganization(authenticatedRequest, org2);
    });

    test.afterEach(async ({authenticatedRequest}) => {
      await deleteOrganization(authenticatedRequest, org1).catch(() => {
        /* ignore cleanup errors */
      });
      await deleteOrganization(authenticatedRequest, org2).catch(() => {
        /* ignore cleanup errors */
      });
    });

    test('filters organizations by name', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/organization');

      // Filter for specific org
      await authenticatedPage.locator('#orgslist-search-input').fill(org1);
      await expect(authenticatedPage.getByText('1 - 1 of 1')).toBeVisible();

      // Reset and filter non-existent
      await authenticatedPage.getByLabel('Reset search').click();
      await authenticatedPage
        .locator('#orgslist-search-input')
        .fill('nonexistent12345');
      await expect(authenticatedPage.getByText('0 - 0 of 0')).toBeVisible();
    });

    test('filters by regex', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/organization');
      await expect(
        authenticatedPage.locator('#filter-input-advanced-search'),
      ).not.toBeVisible();
      await authenticatedPage.getByLabel('Open advanced search').click();
      await expect(
        authenticatedPage.locator('#filter-input-advanced-search'),
      ).toBeVisible();
      await authenticatedPage.locator('#filter-input-regex-checker').click();

      // Use regex to filter - ^search should match org1 (searchtest-xxx)
      await authenticatedPage.locator('#orgslist-search-input').fill('^search');
      await expect(authenticatedPage.getByText(org1)).toBeVisible();
      await expect(authenticatedPage.getByText(org2)).not.toBeVisible();

      // Reset and verify both visible
      await authenticatedPage.getByLabel('Reset search').click();
      await expect(authenticatedPage.getByText(org1)).toBeVisible();
      await expect(authenticatedPage.getByText(org2)).toBeVisible();
    });
  });

  test.describe('pagination', () => {
    const ORG_COUNT = 25;
    const orgPrefix = uniqueName('pagination');
    const orgNames: string[] = [];

    test.beforeAll(async ({browser}) => {
      // Create 25 orgs for pagination testing
      const context = await browser.newContext();
      const request = context.request;

      // Login
      const {getCsrfToken} = await import('../../utils/api/csrf');
      const {API_URL} = await import('../../utils/config');
      const csrfToken = await getCsrfToken(request);
      await request.post(`${API_URL}/api/v1/signin`, {
        headers: {'X-CSRF-Token': csrfToken},
        data: {
          username: TEST_USERS.user.username,
          password: TEST_USERS.user.password,
        },
      });

      // Create orgs
      for (let i = 0; i < ORG_COUNT; i++) {
        const name = `${orgPrefix}${i.toString().padStart(2, '0')}`;
        orgNames.push(name);
        try {
          await createOrganization(request, name);
        } catch {
          // May already exist
        }
      }

      await context.close();
    });

    test.afterAll(async ({browser}) => {
      // Cleanup all created orgs
      const context = await browser.newContext();
      const request = context.request;

      // Login
      const {getCsrfToken} = await import('../../utils/api/csrf');
      const {API_URL} = await import('../../utils/config');
      const csrfToken = await getCsrfToken(request);
      await request.post(`${API_URL}/api/v1/signin`, {
        headers: {'X-CSRF-Token': csrfToken},
        data: {
          username: TEST_USERS.user.username,
          password: TEST_USERS.user.password,
        },
      });

      for (const name of orgNames) {
        await deleteOrganization(request, name).catch(() => {
          /* ignore cleanup errors */
        });
      }

      await context.close();
    });

    test('paginates through organizations', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/organization');

      // Filter to just our test orgs
      await authenticatedPage.locator('#orgslist-search-input').fill(orgPrefix);

      // Verify first page shows 20
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(20);

      // Go to next page
      await authenticatedPage.getByLabel('Go to next page').first().click();
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(5);

      // Go back to first
      await authenticatedPage.getByLabel('Go to first page').first().click();
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(20);
    });
  });

  test(
    'displays avatars for all organizations',
    {tag: ['@PROJQUAY-9749']},
    async ({authenticatedPage, authenticatedRequest}) => {
      // Create a test org
      const orgName = uniqueName('avatartest');
      await createOrganization(authenticatedRequest, orgName);

      try {
        await authenticatedPage.goto('/organization');

        // Filter to our test org
        await authenticatedPage.locator('#orgslist-search-input').fill(orgName);

        // Verify avatar exists
        const orgRow = authenticatedPage
          .locator('tr')
          .filter({hasText: orgName});
        await expect(orgRow.locator('.pf-v5-c-avatar')).toBeVisible();
      } finally {
        await deleteOrganization(authenticatedRequest, orgName).catch(() => {
          /* ignore cleanup errors */
        });
      }
    },
  );

  test.describe('superuser features', {tag: ['@superuser']}, () => {
    test(
      'displays quota column when features enabled',
      {tag: ['@config:QUOTA_MANAGEMENT', '@PROJQUAY-9641']},
      async ({superuserPage, quayConfig}) => {
        test.skip(
          ...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'),
        );

        await superuserPage.goto('/organization');
        await expect(
          superuserPage.locator('th').filter({hasText: 'Size'}),
        ).toBeVisible();
        // Verify quota data is visible
        await expect(
          superuserPage.locator('td[data-label="Size"]').first(),
        ).toBeVisible();
      },
    );

    test('displays user status labels', async ({superuserPage, quayConfig}) => {
      test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

      await superuserPage.goto('/organization');
      // Look for admin user with Superuser label
      await superuserPage
        .locator('#orgslist-search-input')
        .fill(TEST_USERS.admin.username);
      const adminRow = superuserPage
        .locator('tr')
        .filter({hasText: TEST_USERS.admin.username});
      await expect(adminRow.getByText('Superuser')).toBeVisible();
    });

    test('displays global readonly superuser label', async ({
      superuserPage,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

      await superuserPage.goto('/organization');
      // Look for readonly user with Global Readonly Superuser label
      await superuserPage
        .locator('#orgslist-search-input')
        .fill(TEST_USERS.readonly.username);
      const readonlyRow = superuserPage
        .locator('tr')
        .filter({hasText: TEST_USERS.readonly.username});
      await expect(
        readonlyRow.getByText('Global Readonly Superuser'),
      ).toBeVisible();
    });

    test('sees all organizations and users', async ({
      superuserPage,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

      await superuserPage.goto('/organization');

      // Superuser should see their own namespace
      await superuserPage
        .locator('#orgslist-search-input')
        .fill(TEST_USERS.admin.username);
      await expect(
        superuserPage.getByText(TEST_USERS.admin.username),
      ).toBeVisible();

      // Should see other users too
      await superuserPage.getByLabel('Reset search').click();
      await superuserPage
        .locator('#orgslist-search-input')
        .fill(TEST_USERS.user.username);
      await expect(
        superuserPage.getByText(TEST_USERS.user.username),
      ).toBeVisible();
    });
  });

  test.describe(
    'read-only superuser',
    {tag: ['@superuser', '@readonly']},
    () => {
      test('can see all organizations and users', async ({
        readonlyPage,
        quayConfig,
      }) => {
        test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

        await readonlyPage.goto('/organization');

        // Should show user's own namespace
        await expect(
          readonlyPage.getByText(TEST_USERS.readonly.username),
        ).toBeVisible();

        // Should show multiple orgs/users from superuser API
        const orgCount = await readonlyPage
          .locator('td[data-label="Name"]')
          .count();
        expect(orgCount).toBeGreaterThan(0);
      });

      test('cannot perform actions (no kebab menus)', async ({
        readonlyPage,
        quayConfig,
      }) => {
        test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

        await readonlyPage.goto('/organization');

        // Settings column should NOT exist for read-only superusers
        await expect(
          readonlyPage.locator('th').filter({hasText: 'Settings'}),
        ).not.toBeVisible();

        // No kebab menus should be visible
        await expect(
          readonlyPage.locator('[data-testid$="-options-toggle"]'),
        ).toHaveCount(0);

        // Create Organization button SHOULD exist (regular user action)
        await expect(
          readonlyPage.locator('#create-organization-button'),
        ).toBeVisible();

        // Create User button should NOT exist (superuser-only action)
        await expect(
          readonlyPage.getByTestId('create-user-button'),
        ).not.toBeVisible();
      });

      test('cannot select orgs/users they do not own', async ({
        readonlyPage,
        authenticatedRequest,
        quayConfig,
      }) => {
        test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

        // Create an org owned by testuser (not readonly user)
        const testOrg = uniqueName('otherorg');
        await createOrganization(authenticatedRequest, testOrg);

        try {
          await readonlyPage.goto('/organization');

          // Find the row for readonly user's own namespace - should have checkbox
          await readonlyPage
            .locator('#orgslist-search-input')
            .fill(TEST_USERS.readonly.username);
          const ownRow = readonlyPage
            .locator('tr')
            .filter({hasText: TEST_USERS.readonly.username});
          await expect(ownRow.locator('input[type="checkbox"]')).toBeVisible();

          // Find the row for testOrg (not owned) - should NOT have checkbox
          await readonlyPage.getByLabel('Reset search').click();
          await readonlyPage.locator('#orgslist-search-input').fill(testOrg);
          const otherRow = readonlyPage
            .locator('tr')
            .filter({hasText: testOrg});
          await expect(
            otherRow.locator('input[type="checkbox"]'),
          ).not.toBeVisible();
        } finally {
          await deleteOrganization(authenticatedRequest, testOrg).catch(() => {
            /* ignore cleanup errors */
          });
        }
      });
    },
  );

  test.describe('error scenarios', {tag: ['@error']}, () => {
    test('shows user orgs when superuser API fails', async ({
      superuserPage,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'SUPER_USERS'));

      // Mock 403 error for superuser endpoints
      await superuserPage.route('**/api/v1/superuser/organizations/', (route) =>
        route.fulfill({
          status: 403,
          body: JSON.stringify({error: 'Fresh login required'}),
        }),
      );
      await superuserPage.route('**/api/v1/superuser/users/', (route) =>
        route.fulfill({
          status: 403,
          body: JSON.stringify({error: 'Fresh login required'}),
        }),
      );

      await superuserPage.goto('/organization');
      // Should still show user's own organizations
      const orgCount = await superuserPage
        .locator('td[data-label="Name"]')
        .count();
      expect(orgCount).toBeGreaterThan(0);
    });

    test(
      'registry calculation error shows correct modal',
      {tag: ['@PROJQUAY-9874']},
      async ({superuserPage, quayConfig}) => {
        test.skip(
          ...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'),
        );

        // Mock registry size calculation failure
        await superuserPage.route(
          '**/api/v1/superuser/registrysize/',
          (route) => {
            if (route.request().method() === 'POST') {
              return route.fulfill({
                status: 403,
                body: JSON.stringify({error: 'Unauthorized'}),
              });
            }
            return route.fulfill({
              status: 200,
              body: JSON.stringify({
                size_bytes: 0,
                last_ran: null,
                queued: false,
                running: false,
              }),
            });
          },
        );

        await superuserPage.goto('/organization');
        await superuserPage.getByRole('button', {name: 'Calculate'}).click();
        await superuserPage
          .locator('.pf-v5-c-modal-box')
          .getByRole('button', {name: 'Calculate'})
          .click();

        // Verify correct error modal title
        await expect(
          superuserPage.getByText('Registry calculation failed'),
        ).toBeVisible();
        await expect(
          superuserPage.getByText('Org deletion failed'),
        ).not.toBeVisible();
      },
    );

    test(
      'displays "0.00 KiB" for zero registry size',
      {tag: ['@PROJQUAY-9860']},
      async ({superuserPage, quayConfig}) => {
        test.skip(
          ...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'),
        );

        // Mock registry size with 0 bytes
        await superuserPage.route(
          '**/api/v1/superuser/registrysize/',
          (route) => {
            return route.fulfill({
              status: 200,
              body: JSON.stringify({
                size_bytes: 0,
                last_ran: 1733241830,
                queued: false,
                running: false,
              }),
            });
          },
        );

        await superuserPage.goto('/organization');

        // Verify the header displays "0.00 KiB" instead of "N/A"
        await expect(
          superuserPage.getByText('Total Registry Size: 0.00 KiB'),
        ).toBeVisible();
      },
    );
  });

  test.describe('quota features', {tag: ['@quota']}, () => {
    test(
      'regular user sees quota column',
      {tag: ['@PROJQUAY-9641']},
      async ({authenticatedPage, authenticatedRequest, quayConfig}) => {
        test.skip(
          ...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'),
        );

        // Create a test org
        const orgName = uniqueName('quotatest');
        await createOrganization(authenticatedRequest, orgName);

        try {
          await authenticatedPage.goto('/organization');

          // Verify the Size column header exists
          await expect(
            authenticatedPage.locator('th').filter({hasText: 'Size'}),
          ).toBeVisible();

          // Verify quota data cells are visible
          await expect(
            authenticatedPage.locator('td[data-label="Size"]').first(),
          ).toBeVisible();
        } finally {
          await deleteOrganization(authenticatedRequest, orgName).catch(() => {
            /* ignore cleanup errors */
          });
        }
      },
    );

    test(
      'user sees own namespace quota',
      {tag: ['@PROJQUAY-9886']},
      async ({authenticatedPage, quayConfig}) => {
        test.skip(
          ...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'),
        );

        await authenticatedPage.goto('/organization');

        // Find the user's own namespace row
        await authenticatedPage
          .locator('#orgslist-search-input')
          .fill(TEST_USERS.user.username);
        const userRow = authenticatedPage
          .locator('tr')
          .filter({hasText: TEST_USERS.user.username});

        // The Size column should exist for the user's namespace
        await expect(userRow.locator('td[data-label="Size"]')).toBeVisible();
      },
    );
  });
});
