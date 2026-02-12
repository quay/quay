import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Organization List',
  {tag: ['@organization', '@critical']},
  () => {
    test('search and filtering', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/organization');

      // Wait for the table to load
      await expect(
        authenticatedPage.locator('td[data-label="Name"]').first(),
      ).toBeVisible();

      // Test basic search - search for current user
      const searchInput = authenticatedPage.getByPlaceholder(/Search by/);
      await searchInput.fill(TEST_USERS.user.username);

      // Should find the user's namespace
      await expect(
        authenticatedPage.getByRole('link', {name: TEST_USERS.user.username}),
      ).toBeVisible();

      // Reset search
      await authenticatedPage.locator('[aria-label="Reset search"]').click();

      // Search for non-existent org
      await searchInput.fill('nonexistent_org_xyz_123456');
      await expect(
        authenticatedPage.locator(
          '[data-testid="orgslist-pagination"] .pf-v5-c-pagination__total-items',
        ),
      ).toContainText('0 - 0 of 0');
      await authenticatedPage.locator('[aria-label="Reset search"]').click();

      // Test regex search via advanced search
      await expect(
        authenticatedPage.locator('[id="filter-input-advanced-search"]'),
      ).not.toBeVisible();
      await authenticatedPage
        .locator('[aria-label="Open advanced search"]')
        .click();
      await expect(
        authenticatedPage.locator('[id="filter-input-advanced-search"]'),
      ).toBeVisible();
      await authenticatedPage
        .locator('[id="filter-input-regex-checker"]')
        .click();

      // Search with regex pattern starting with 't' (should match testuser)
      await searchInput.fill(`^${TEST_USERS.user.username.charAt(0)}`);
      await expect(
        authenticatedPage.getByRole('link', {name: TEST_USERS.user.username}),
      ).toBeVisible();

      // Reset and verify results restored
      await authenticatedPage.locator('[aria-label="Reset search"]').click();
      await expect(
        authenticatedPage.getByRole('link', {name: TEST_USERS.user.username}),
      ).toBeVisible();
    });

    test('pagination', async ({authenticatedPage, api}) => {
      // Create multiple organizations to ensure pagination (in parallel for speed)
      const orgPromises = Array.from({length: 25}, () =>
        api.organization('paginationtest'),
      );
      const orgs = await Promise.all(orgPromises);

      await authenticatedPage.goto('/organization');

      // Filter to our test orgs to ensure we're testing pagination of known data
      await authenticatedPage
        .getByPlaceholder(/Search by/)
        .fill('paginationtest');

      // Wait for results to load
      await expect(
        authenticatedPage.locator('td[data-label="Name"]').first(),
      ).toBeVisible();

      // Should show pagination (20 per page default, so 25 orgs = 2 pages)
      await expect(
        authenticatedPage.locator(
          '[data-testid="orgslist-pagination"] .pf-v5-c-pagination__total-items',
        ),
      ).toContainText(/1 - 20 of \d+/);
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(20);

      // Go to next page
      await authenticatedPage
        .locator('button[aria-label="Go to next page"]')
        .first()
        .click();
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(5);

      // Go to first page
      await authenticatedPage
        .locator('button[aria-label="Go to first page"]')
        .first()
        .click();
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(20);

      // Go to last page
      await authenticatedPage
        .locator('button[aria-label="Go to last page"]')
        .first()
        .click();
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(5);

      // Change per page - click the pagination per-page dropdown then select option
      await authenticatedPage
        .locator('[data-testid="orgslist-pagination"] button')
        .first()
        .click();
      await authenticatedPage.getByText('10 per page').click();

      // After changing per-page, we're reset to page 1 with 10 items
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(10);

      // Go to last page and verify remaining items (25 orgs / 10 per page = 5 on last page)
      await authenticatedPage
        .locator('button[aria-label="Go to last page"]')
        .first()
        .click();
      await expect(
        authenticatedPage.locator('td[data-label="Name"]'),
      ).toHaveCount(5);
    });

    test(
      'organization CRUD lifecycle',
      {tag: ['@PROJQUAY-9948', '@PROJQUAY-9843']},
      async ({authenticatedPage, quayConfig, api}) => {
        const mailingEnabled = quayConfig?.features?.MAILING === true;

        await authenticatedPage.goto('/organization');

        // Create a shared unique ID for both orgs so we can filter them together
        const testId = `${Date.now()}-${Math.random()
          .toString(36)
          .substring(2, 8)}`;
        const orgName = `crud1-${testId}`;
        const orgName2 = `crud2-${testId}`;
        const orgEmail = `${orgName}@example.com`;

        // Open and cancel modal first
        await authenticatedPage.locator('#create-organization-button').click();
        await expect(
          authenticatedPage.locator('#create-org-cancel'),
        ).toBeVisible();
        await authenticatedPage.locator('#create-org-cancel').click();
        await expect(
          authenticatedPage.locator('#create-org-cancel'),
        ).not.toBeVisible();

        // Create organization
        await authenticatedPage.locator('#create-organization-button').click();
        await authenticatedPage.locator('#create-org-name-input').fill(orgName);
        if (mailingEnabled) {
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(orgEmail);
        }

        // Wait for Create button to be enabled, then click and wait for API response
        await expect(
          authenticatedPage.locator('#create-org-confirm'),
        ).toBeEnabled();
        await Promise.all([
          authenticatedPage.waitForResponse(
            (resp) =>
              resp.url().includes('/api/v1/organization/') &&
              resp.request().method() === 'POST',
          ),
          authenticatedPage.locator('#create-org-confirm').click(),
        ]);

        // Wait for modal to close (indicates successful creation)
        await expect(
          authenticatedPage.locator('#create-org-cancel'),
        ).not.toBeVisible({timeout: 10000});

        // Verify success message appears
        await expect(
          authenticatedPage.getByText(
            `Successfully created organization ${orgName}`,
          ),
        ).toBeVisible();

        // Search for created org
        await authenticatedPage.getByPlaceholder(/Search by/).fill(orgName);
        await expect(
          authenticatedPage.locator(
            '[data-testid="orgslist-pagination"] .pf-v5-c-pagination__total-items',
          ),
        ).toContainText('1 - 1 of 1');

        // PROJQUAY-9948: Try to create org with same name - should show error, not success
        await authenticatedPage.locator('#create-organization-button').click();
        await authenticatedPage.locator('#create-org-name-input').fill(orgName);
        if (mailingEnabled) {
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(`duplicate-${orgEmail}`);
        }
        await authenticatedPage.locator('#create-org-confirm').click();

        // Should show error message
        await expect(
          authenticatedPage.getByText(
            'A user or organization with this name already exists',
          ),
        ).toBeVisible();

        // Modal should still be open
        await expect(
          authenticatedPage.locator('#create-org-cancel'),
        ).toBeVisible();
        await authenticatedPage.locator('#create-org-cancel').click();

        // Validate form validation - confirm button disabled without required fields
        await authenticatedPage.locator('#create-organization-button').click();
        await expect(
          authenticatedPage.locator('#create-org-confirm'),
        ).toBeDisabled();
        await authenticatedPage
          .locator('#create-org-name-input')
          .fill('validname');
        if (mailingEnabled) {
          // When mailing is enabled, button should still be disabled without email
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeDisabled();
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill('invalid');
          await authenticatedPage.locator('#create-org-name-input').click(); // Trigger validation
          await expect(
            authenticatedPage.getByText(
              'Enter a valid email: email@provider.com',
            ),
          ).toBeVisible();
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeDisabled();
        } else {
          // When mailing is disabled, button should be enabled with just a name
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeEnabled();
        }
        await authenticatedPage.locator('#create-org-cancel').click();

        // PROJQUAY-9843: Create second org for bulk delete test
        await authenticatedPage.locator('[aria-label="Reset search"]').click();
        await authenticatedPage.locator('#create-organization-button').click();
        await authenticatedPage
          .locator('#create-org-name-input')
          .fill(orgName2);
        if (mailingEnabled) {
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(`${orgName2}@example.com`);
        }
        await expect(
          authenticatedPage.locator('#create-org-confirm'),
        ).toBeEnabled();
        await Promise.all([
          authenticatedPage.waitForResponse(
            (resp) =>
              resp.url().includes('/api/v1/organization/') &&
              resp.request().method() === 'POST',
          ),
          authenticatedPage.locator('#create-org-confirm').click(),
        ]);
        await expect(
          authenticatedPage.locator('#create-org-cancel'),
        ).not.toBeVisible({timeout: 10000});
        await expect(
          authenticatedPage.getByText(
            `Successfully created organization ${orgName2}`,
          ),
        ).toBeVisible();

        // Filter to show both test orgs using the shared test ID
        await authenticatedPage.getByPlaceholder(/Search by/).fill(testId);

        // Verify both orgs are visible
        await expect(
          authenticatedPage.getByRole('link', {name: orgName}),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByRole('link', {name: orgName2}),
        ).toBeVisible();

        // PROJQUAY-9843: Select both orgs and delete via bulk delete
        const row1 = authenticatedPage.locator('tr').filter({
          has: authenticatedPage.getByRole('link', {name: orgName}),
        });
        await expect(row1).toBeVisible();
        await row1.locator('input[type="checkbox"]').check();

        const row2 = authenticatedPage.locator('tr').filter({
          has: authenticatedPage.getByRole('link', {name: orgName2}),
        });
        await row2.locator('input[type="checkbox"]').check();

        // Open bulk delete modal
        await authenticatedPage.getByRole('button', {name: 'Actions'}).click();
        await authenticatedPage.getByRole('menuitem', {name: 'Delete'}).click();

        // Verify both orgs are in deletion list
        const bulkDeleteModal = authenticatedPage.locator(
          '[id="bulk-delete-modal"]',
        );
        await expect(bulkDeleteModal.getByText(orgName)).toBeVisible();
        await expect(bulkDeleteModal.getByText(orgName2)).toBeVisible();

        // Complete deletion
        await authenticatedPage
          .getByTestId('delete-confirmation-input')
          .fill('confirm');
        await authenticatedPage.getByTestId('bulk-delete-confirm-btn').click();

        // Wait for modal to close (indicates successful deletion)
        await expect(bulkDeleteModal).not.toBeVisible();

        // Verify orgs are gone after deletion
        await expect(
          authenticatedPage.getByRole('link', {name: orgName}),
        ).not.toBeVisible();
        await expect(
          authenticatedPage.getByRole('link', {name: orgName2}),
        ).not.toBeVisible();
      },
    );

    test(
      'displays avatars',
      {tag: '@PROJQUAY-9749'},
      async ({authenticatedPage}) => {
        await authenticatedPage.goto('/organization');

        // Wait for table to load
        await expect(
          authenticatedPage.locator('td[data-label="Name"]').first(),
        ).toBeVisible();

        // Search for the current user's namespace (user namespaces have avatars)
        await authenticatedPage
          .getByPlaceholder(/Search by/)
          .fill(TEST_USERS.user.username);

        // Verify the user's row has an avatar
        const userRow = authenticatedPage.locator('tr').filter({
          has: authenticatedPage.getByRole('link', {
            name: TEST_USERS.user.username,
          }),
        });
        await expect(userRow.locator('.pf-v5-c-avatar')).toBeVisible();
      },
    );

    test.describe(
      'Superuser Features',
      {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
      () => {
        test('displays user status labels', async ({superuserPage}) => {
          await superuserPage.goto('/organization');

          // Wait for table to load
          await expect(
            superuserPage.locator('td[data-label="Name"]').first(),
          ).toBeVisible();

          // Search for admin (superuser) and verify label
          await superuserPage
            .getByPlaceholder(/Search by/)
            .fill(TEST_USERS.admin.username);
          const adminRow = superuserPage.locator('tr').filter({
            has: superuserPage.getByRole('link', {
              name: TEST_USERS.admin.username,
            }),
          });
          await expect(adminRow.getByText('Superuser')).toBeVisible();

          // Search for readonly user and verify "Global Readonly Superuser" label with cyan color
          await superuserPage.locator('[aria-label="Reset search"]').click();
          await superuserPage
            .getByPlaceholder(/Search by/)
            .fill(TEST_USERS.readonly.username);
          const readonlyRow = superuserPage.locator('tr').filter({
            has: superuserPage.getByRole('link', {
              name: TEST_USERS.readonly.username,
            }),
          });
          await expect(
            readonlyRow.getByText('Global Readonly Superuser'),
          ).toBeVisible();
          await expect(
            readonlyRow
              .locator('.pf-v5-c-label.pf-m-cyan')
              .getByText('Global Readonly Superuser'),
          ).toBeVisible();

          // Verify regular superuser doesn't have "Global Readonly Superuser" label
          await superuserPage.locator('[aria-label="Reset search"]').click();
          await superuserPage
            .getByPlaceholder(/Search by/)
            .fill(TEST_USERS.admin.username);
          const adminRowAgain = superuserPage.locator('tr').filter({
            has: superuserPage.getByRole('link', {
              name: TEST_USERS.admin.username,
            }),
          });
          await expect(adminRowAgain.getByText('Superuser')).toBeVisible();
          await expect(
            adminRowAgain.getByText('Global Readonly Superuser'),
          ).not.toBeVisible();
        });

        test('shows user orgs when superuser API fails', async ({
          superuserPage,
          superuserApi,
        }) => {
          // Create an org that the superuser owns
          const ownedOrg = await superuserApi.organization('ownedbyadmin');

          // Mock superuser API endpoints to return 403 (fresh login required)
          await superuserPage.route(
            '**/api/v1/superuser/organizations/',
            async (route) => {
              await route.fulfill({
                status: 403,
                body: JSON.stringify({error: 'Fresh login required'}),
              });
            },
          );
          await superuserPage.route(
            '**/api/v1/superuser/users/',
            async (route) => {
              await route.fulfill({
                status: 403,
                body: JSON.stringify({error: 'Fresh login required'}),
              });
            },
          );

          await superuserPage.goto('/organization');

          // Wait for table to load
          await expect(
            superuserPage.locator('td[data-label="Name"]').first(),
          ).toBeVisible();

          // Should still show superuser's own organizations and namespace
          await expect(
            superuserPage.getByRole('link', {
              name: TEST_USERS.admin.username,
              exact: true,
            }),
          ).toBeVisible();
          await expect(
            superuserPage.getByRole('link', {name: ownedOrg.name, exact: true}),
          ).toBeVisible();
        });

        test('shows combined orgs and no duplicates', async ({
          superuserPage,
          superuserApi,
        }) => {
          // Create an org for testing
          const testOrg = await superuserApi.organization('combinedtest');

          await superuserPage.goto('/organization');

          // Wait for table to load
          await expect(
            superuserPage.locator('td[data-label="Name"]').first(),
          ).toBeVisible();

          // Search for the test org
          await superuserPage.getByPlaceholder(/Search by/).fill(testOrg.name);

          // Should show exactly once (no duplicates)
          await expect(
            superuserPage.locator(
              '[data-testid="orgslist-pagination"] .pf-v5-c-pagination__total-items',
            ),
          ).toContainText('1 - 1 of 1');
          const orgLinks = superuserPage.getByRole('link', {
            name: testOrg.name,
            exact: true,
          });
          await expect(orgLinks).toHaveCount(1);
        });
      },
    );

    test.describe(
      'Read-only Superuser',
      {tag: '@feature:SUPERUSERS_FULL_ACCESS'},
      () => {
        test('can see orgs but cannot perform actions', async ({
          readonlyPage,
          superuserApi,
        }) => {
          // Create orgs that readonly user doesn't own
          const otherOrg = await superuserApi.organization('readonlytest');

          await readonlyPage.goto('/organization');

          // Wait for table to load
          await expect(
            readonlyPage.locator('td[data-label="Name"]').first(),
          ).toBeVisible();

          // Can see all orgs/users
          await expect(
            readonlyPage.getByRole('link', {
              name: TEST_USERS.readonly.username,
              exact: true,
            }),
          ).toBeVisible();
          await expect(
            readonlyPage.getByRole('link', {name: otherOrg.name, exact: true}),
          ).toBeVisible();

          // Settings column header should NOT exist for read-only superusers
          await expect(
            readonlyPage.locator('th').getByText('Settings'),
          ).not.toBeVisible();

          // No kebab menus should be visible (canModify = false)
          await expect(
            readonlyPage.locator('[data-testid$="-options-toggle"]'),
          ).not.toBeVisible();

          // Create Organization button SHOULD exist (regular user action)
          await expect(
            readonlyPage.locator('#create-organization-button'),
          ).toBeVisible();

          // Create User button should NOT exist (superuser-only action)
          await expect(
            readonlyPage.locator('[data-testid="create-user-button"]'),
          ).not.toBeVisible();

          // Can't select orgs they don't own - search for other org
          await readonlyPage.getByPlaceholder(/Search by/).fill(otherOrg.name);
          const otherOrgRow = readonlyPage.locator('tr').filter({
            has: readonlyPage.getByRole('link', {name: otherOrg.name}),
          });
          await expect(
            otherOrgRow.locator('input[type="checkbox"]'),
          ).not.toBeVisible();

          // Can select own namespace
          await readonlyPage.locator('[aria-label="Reset search"]').click();
          await readonlyPage
            .getByPlaceholder(/Search by/)
            .fill(TEST_USERS.readonly.username);
          const ownRow = readonlyPage.locator('tr').filter({
            has: readonlyPage.getByRole('link', {
              name: TEST_USERS.readonly.username,
            }),
          });
          await expect(ownRow.locator('input[type="checkbox"]')).toBeVisible();
        });
      },
    );

    test.describe(
      'Quota Management',
      {tag: ['@feature:QUOTA_MANAGEMENT', '@feature:EDIT_QUOTA']},
      () => {
        test(
          'superuser displays quota consumed column',
          {tag: '@PROJQUAY-9641'},
          async ({superuserPage, superuserApi}) => {
            // Create org with quota
            const org = await superuserApi.organization('quotatest');
            await superuserApi.quota(org.name, 10737418240); // 10 GiB

            await superuserPage.goto('/organization');

            // Verify Size column exists for superusers
            await expect(
              superuserPage.locator('th').getByText('Size'),
            ).toBeVisible();

            // Search for our test org and verify quota data is visible
            await superuserPage.getByPlaceholder(/Search by/).fill(org.name);
            const orgRow = superuserPage.locator('tr').filter({
              has: superuserPage.getByRole('link', {name: org.name}),
            });
            const sizeCell = orgRow.locator('td[data-label="Size"]');
            await expect(sizeCell).toBeVisible();
            // Should show quota data, not just a dash
            // (actual value depends on what's in the org)
          },
        );

        test(
          'regular user sees their own namespace quota',
          {tag: '@PROJQUAY-9886'},
          async ({authenticatedPage, superuserApi}) => {
            // Superuser creates quota for the test user's namespace (uses superuser API for user namespaces)
            await superuserApi.userQuota(TEST_USERS.user.username, 10737418240);

            await authenticatedPage.goto('/organization');

            // Verify Size column exists
            await expect(
              authenticatedPage.locator('th').getByText('Size'),
            ).toBeVisible();

            // Find user's own namespace row and verify quota is displayed
            await authenticatedPage
              .getByPlaceholder(/Search by/)
              .fill(TEST_USERS.user.username);
            const userRow = authenticatedPage.locator('tr').filter({
              has: authenticatedPage.getByRole('link', {
                name: TEST_USERS.user.username,
              }),
            });
            const sizeCell = userRow.locator('td[data-label="Size"]');
            await expect(sizeCell).toBeVisible();
            // Verify it shows GiB format (quota is configured)
            await expect(sizeCell).toContainText('GiB');
          },
        );

        test(
          'registry calculation error shows correct modal title',
          {tag: '@PROJQUAY-9874'},
          async ({superuserPage}) => {
            // Mock registry size endpoints
            await superuserPage.route(
              '**/api/v1/superuser/registrysize/',
              async (route) => {
                if (route.request().method() === 'GET') {
                  await route.fulfill({
                    status: 200,
                    body: JSON.stringify({
                      size_bytes: 0,
                      last_ran: null,
                      queued: false,
                      running: false,
                    }),
                  });
                } else if (route.request().method() === 'POST') {
                  await route.fulfill({
                    status: 403,
                    body: JSON.stringify({error: 'Unauthorized'}),
                  });
                }
              },
            );

            await superuserPage.goto('/organization');

            // Click Calculate button
            await superuserPage
              .getByRole('button', {name: 'Calculate'})
              .click();

            // Confirm in modal
            await superuserPage
              .getByRole('dialog')
              .getByRole('button', {name: 'Calculate'})
              .click();

            // Verify error modal shows correct title
            await expect(
              superuserPage
                .getByRole('dialog')
                .getByText('Registry calculation failed'),
            ).toBeVisible();
            // Should NOT show "Org deletion failed"
            await expect(
              superuserPage
                .getByRole('dialog')
                .getByText('Org deletion failed'),
            ).not.toBeVisible();
          },
        );

        test(
          'displays "0.00 KiB" for zero registry size',
          {tag: '@PROJQUAY-9860'},
          async ({superuserPage}) => {
            // Mock registry size endpoint with 0 bytes
            await superuserPage.route(
              '**/api/v1/superuser/registrysize/',
              async (route) => {
                await route.fulfill({
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

            // Verify header displays "0.00 KiB" instead of "N/A"
            await expect(
              superuserPage.getByText('Total Registry Size:'),
            ).toBeVisible();
            await expect(
              superuserPage.getByText('Total Registry Size: 0.00 KiB'),
            ).toBeVisible();

            // Verify "N/A" is NOT displayed for registry size
            const registrySizeText = superuserPage
              .locator('text=Total Registry Size:')
              .locator('..');
            await expect(registrySizeText).not.toContainText('N/A');
          },
        );
      },
    );
    test(
      'create organization respects FEATURE_MAILING for email field',
      {tag: '@PROJQUAY-10500'},
      async ({authenticatedPage, quayConfig, api}) => {
        const mailingEnabled = quayConfig?.features?.MAILING === true;

        await authenticatedPage.goto('/organization');

        // Open create organization modal
        await authenticatedPage.locator('#create-organization-button').click();
        await expect(
          authenticatedPage.locator('#create-org-name-input'),
        ).toBeVisible();

        if (mailingEnabled) {
          // When MAILING is enabled, email field should be visible and required
          await expect(
            authenticatedPage.locator('#create-org-email-input'),
          ).toBeVisible();

          // Fill only name - button should be disabled (email required)
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill('testmailingorg');
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeDisabled();
        } else {
          // When MAILING is disabled, email field should NOT be visible
          await expect(
            authenticatedPage.locator('#create-org-email-input'),
          ).not.toBeVisible();

          // Fill only name - button should be enabled (email not required)
          const orgName = uniqueName('mailtest');
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName);
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeEnabled();

          // Create org without email should succeed
          await Promise.all([
            authenticatedPage.waitForResponse(
              (resp) =>
                resp.url().includes('/api/v1/organization/') &&
                resp.request().method() === 'POST' &&
                resp.status() === 201,
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);

          // Modal should close on success
          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          await expect(
            authenticatedPage.getByText(
              `Successfully created organization ${orgName}`,
            ),
          ).toBeVisible();

          // Clean up the org created via UI
          await api.raw.deleteOrganization(orgName);
        }

        // Close modal if still open
        const cancelButton = authenticatedPage.locator('#create-org-cancel');
        if (await cancelButton.isVisible()) {
          await cancelButton.click();
        }
      },
    );
  },
);
