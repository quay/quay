import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {API_URL} from '../../utils/config';

test.describe(
  'Contact Email for Organizations',
  {tag: ['@organization', '@PROJQUAY-6975']},
  () => {
    // =========================================================================
    // Group 1: Create Organization Modal — Contact Email
    // =========================================================================

    test.describe(
      'Create Organization Modal — Contact Email',
      {tag: ['@PROJQUAY-10592']},
      () => {
        test('field is always visible with correct label and helper text', async ({
          authenticatedPage,
        }) => {
          await authenticatedPage.goto('/organization');
          await authenticatedPage
            .locator('#create-organization-button')
            .click();

          // Field always visible regardless of FEATURE_MAILING
          const emailInput = authenticatedPage.locator(
            '#create-org-email-input',
          );
          await expect(emailInput).toBeVisible();

          // Label is "Contact Email (Optional)"
          await expect(
            authenticatedPage.getByText('Contact Email (Optional)'),
          ).toBeVisible();

          // Helper text describes purpose
          await expect(
            authenticatedPage.getByText(
              'Optional. Used for organization recovery and notifications.',
            ),
          ).toBeVisible();

          await authenticatedPage.locator('#create-org-cancel').click();
        });

        test('creates org with only a name (no email)', async ({
          authenticatedPage,
          api,
        }) => {
          await authenticatedPage.goto('/organization');

          const orgName = uniqueName('noemail');
          await authenticatedPage
            .locator('#create-organization-button')
            .click();
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName);

          // Email field should be empty and Create button should be enabled
          await expect(
            authenticatedPage.locator('#create-org-email-input'),
          ).toHaveValue('');
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeEnabled();

          // Create and wait for API response
          const [response] = await Promise.all([
            authenticatedPage.waitForResponse(
              (resp) =>
                resp.url().includes('/api/v1/organization/') &&
                resp.request().method() === 'POST',
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);

          expect(response.status()).toBe(201);

          // Modal closes on success
          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          await expect(
            authenticatedPage.getByText(
              `Successfully created organization ${orgName}`,
            ),
          ).toBeVisible();

          // Clean up
          await api.raw.deleteOrganization(orgName);
        });

        test('creates org with name and contact email (sends contact_email in POST)', async ({
          authenticatedPage,
          api,
        }) => {
          await authenticatedPage.goto('/organization');

          const orgName = uniqueName('withemail');
          const email = `${orgName}@example.com`;
          await authenticatedPage
            .locator('#create-organization-button')
            .click();
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName);
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(email);

          // Intercept POST to verify payload
          const [request] = await Promise.all([
            authenticatedPage.waitForRequest(
              (req) =>
                req.url().includes('/api/v1/organization/') &&
                req.method() === 'POST',
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);

          const body = request.postDataJSON();
          expect(body).toHaveProperty('contact_email', email);
          expect(body).not.toHaveProperty('email');

          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          await expect(
            authenticatedPage.getByText(
              `Successfully created organization ${orgName}`,
            ),
          ).toBeVisible();

          // Clean up
          await api.raw.deleteOrganization(orgName);
        });

        test('validates email format: invalid → error → clear → no error', async ({
          authenticatedPage,
        }) => {
          await authenticatedPage.goto('/organization');
          await authenticatedPage
            .locator('#create-organization-button')
            .click();

          await authenticatedPage
            .locator('#create-org-name-input')
            .fill('validname');

          // Type invalid email
          const emailInput = authenticatedPage.locator(
            '#create-org-email-input',
          );
          await emailInput.fill('not-an-email');
          await authenticatedPage.locator('#create-org-name-input').click(); // blur

          await expect(
            authenticatedPage.getByText(
              'Enter a valid email: email@provider.com',
            ),
          ).toBeVisible();
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeDisabled();

          // Clear email — error should disappear, button enabled (email optional)
          await emailInput.clear();
          await authenticatedPage.locator('#create-org-name-input').click(); // blur

          await expect(
            authenticatedPage.getByText(
              'Enter a valid email: email@provider.com',
            ),
          ).not.toBeVisible();
          await expect(
            authenticatedPage.locator('#create-org-confirm'),
          ).toBeEnabled();

          await authenticatedPage.locator('#create-org-cancel').click();
        });

        test('two orgs can share the same contact email', async ({
          authenticatedPage,
          api,
        }) => {
          await authenticatedPage.goto('/organization');

          const sharedEmail = `shared-${Date.now()}@example.com`;

          // Create first org
          const orgName1 = uniqueName('shared');
          await authenticatedPage
            .locator('#create-organization-button')
            .click();
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName1);
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(sharedEmail);

          const [resp1] = await Promise.all([
            authenticatedPage.waitForResponse(
              (resp) =>
                resp.url().includes('/api/v1/organization/') &&
                resp.request().method() === 'POST',
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);
          expect(resp1.status()).toBe(201);
          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          // Create second org with same email
          const orgName2 = uniqueName('shared');
          await authenticatedPage
            .locator('#create-organization-button')
            .click();
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName2);
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(sharedEmail);

          const [resp2] = await Promise.all([
            authenticatedPage.waitForResponse(
              (resp) =>
                resp.url().includes('/api/v1/organization/') &&
                resp.request().method() === 'POST',
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);
          expect(resp2.status()).toBe(201);
          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          // Clean up
          await api.raw.deleteOrganization(orgName1);
          await api.raw.deleteOrganization(orgName2);
        });
      },
    );

    // =========================================================================
    // Group 2: Organization Settings — Contact Email Management
    // =========================================================================

    test.describe(
      'Organization Settings — Contact Email',
      {tag: ['@PROJQUAY-10593']},
      () => {
        test('displays contact email in settings (not UUID)', async ({
          authenticatedPage,
          api,
        }) => {
          const contactEmail = 'org-display@example.com';
          const org = await api.organization('display', contactEmail);

          await authenticatedPage.goto(
            `/organization/${org.name}?tab=Settings`,
          );

          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toBeVisible();
          await expect(emailInput).toHaveValue(contactEmail);

          // Verify it's NOT a UUID
          const value = await emailInput.inputValue();
          expect(value).not.toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-/);
        });

        test('shows "Contact Email" label for orgs, validates, and shows helper text', async ({
          authenticatedPage,
          api,
        }) => {
          const org = await api.organization('labelvld');

          await authenticatedPage.goto(
            `/organization/${org.name}?tab=Settings`,
          );

          // Label is "Contact Email" for orgs
          await expect(
            authenticatedPage.getByText('Contact Email'),
          ).toBeVisible();

          // Helper text
          await expect(
            authenticatedPage.getByText(
              'Optional. Used for organization recovery and billing notifications.',
            ),
          ).toBeVisible();

          // Validation: type invalid email
          const emailInput = authenticatedPage.locator('#org-settings-email');
          await emailInput.clear();
          await emailInput.fill('invalid-email');

          await expect(
            authenticatedPage.getByText('Please enter a valid email address'),
          ).toBeVisible();

          const saveButton = authenticatedPage.locator('#save-org-settings');
          await expect(saveButton).toBeDisabled();

          // Type valid email — error clears, save enabled
          await emailInput.clear();
          await emailInput.fill('valid@example.com');
          await expect(
            authenticatedPage.getByText('Please enter a valid email address'),
          ).not.toBeVisible();
          await expect(saveButton).toBeEnabled();
        });

        test('updates contact email and persists after reload', async ({
          authenticatedPage,
          api,
        }) => {
          const org = await api.organization('update');

          await authenticatedPage.goto(
            `/organization/${org.name}?tab=Settings`,
          );

          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toBeVisible();

          const newEmail = 'updated@example.com';
          await emailInput.clear();
          await emailInput.fill(newEmail);

          // Verify PUT sends contact_email
          const putPromise = authenticatedPage.waitForRequest(
            (req) =>
              req.url().includes(`/api/v1/organization/${org.name}`) &&
              req.method() === 'PUT',
          );

          await authenticatedPage.locator('#save-org-settings').click();

          const putRequest = await putPromise;
          const body = putRequest.postDataJSON();
          expect(body).toHaveProperty('contact_email');

          await expect(
            authenticatedPage.getByText('Successfully updated settings').first(),
          ).toBeVisible();

          // Reload and verify persistence
          await authenticatedPage.reload();
          await expect(emailInput).toHaveValue(newEmail);
        });

        test('clears contact email (sets to empty)', async ({
          authenticatedPage,
          api,
        }) => {
          const org = await api.organization(
            'clremail',
            'to-be-cleared@example.com',
          );

          await authenticatedPage.goto(
            `/organization/${org.name}?tab=Settings`,
          );

          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toHaveValue('to-be-cleared@example.com');

          await emailInput.clear();
          await authenticatedPage.locator('#save-org-settings').click();
          await expect(
            authenticatedPage.getByText('Successfully updated settings').first(),
          ).toBeVisible();

          await authenticatedPage.reload();
          await expect(emailInput).toHaveValue('');
        });

        test('allows same email as another org in settings', async ({
          authenticatedPage,
          api,
        }) => {
          const sharedEmail = 'settings-shared@company.com';
          await api.organization('shset1', sharedEmail);
          const org2 = await api.organization('shset2');

          await authenticatedPage.goto(
            `/organization/${org2.name}?tab=Settings`,
          );

          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toBeVisible();
          await emailInput.clear();
          await emailInput.fill(sharedEmail);
          await authenticatedPage.locator('#save-org-settings').click();

          await expect(
            authenticatedPage.getByText('Successfully updated settings').first(),
          ).toBeVisible();
        });

        test('user account settings still show "Email" label', async ({
          authenticatedPage,
        }) => {
          const username = TEST_USERS.user.username;
          await authenticatedPage.goto(`/user/${username}?tab=Settings`);

          // "Contact Email" should NOT be present on user settings
          await expect(
            authenticatedPage.getByText('Contact Email'),
          ).not.toBeVisible();
        });
      },
    );

    // =========================================================================
    // Group 3: End-to-End Lifecycle Flows
    // =========================================================================

    test.describe(
      'Contact Email — E2E Lifecycle',
      {tag: ['@critical']},
      () => {
        test('create org with contact email → verify in settings → update → verify persistence', async ({
          authenticatedPage,
          api,
        }) => {
          await authenticatedPage.goto('/organization');

          const orgName = uniqueName('lifecycle');
          const initialEmail = `${orgName}@example.com`;
          const updatedEmail = `updated-${orgName}@example.com`;

          // Create org with contact email via UI
          await authenticatedPage
            .locator('#create-organization-button')
            .click();
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName);
          await authenticatedPage
            .locator('#create-org-email-input')
            .fill(initialEmail);

          await Promise.all([
            authenticatedPage.waitForResponse(
              (resp) =>
                resp.url().includes('/api/v1/organization/') &&
                resp.request().method() === 'POST' &&
                resp.status() === 201,
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);

          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          // Navigate to settings and verify email appears
          await authenticatedPage.goto(
            `/organization/${orgName}?tab=Settings`,
          );
          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toHaveValue(initialEmail);

          // Update the email
          await emailInput.clear();
          await emailInput.fill(updatedEmail);
          await authenticatedPage.locator('#save-org-settings').click();
          await expect(
            authenticatedPage.getByText('Successfully updated settings').first(),
          ).toBeVisible();

          // Reload and verify persistence
          await authenticatedPage.reload();
          await expect(emailInput).toHaveValue(updatedEmail);

          // Clean up
          await api.raw.deleteOrganization(orgName);
        });

        test('create org without email → add email in settings → verify', async ({
          authenticatedPage,
          api,
        }) => {
          await authenticatedPage.goto('/organization');

          const orgName = uniqueName('noemailset');
          const addedEmail = `added-${orgName}@example.com`;

          // Create org without email
          await authenticatedPage
            .locator('#create-organization-button')
            .click();
          await authenticatedPage
            .locator('#create-org-name-input')
            .fill(orgName);

          await Promise.all([
            authenticatedPage.waitForResponse(
              (resp) =>
                resp.url().includes('/api/v1/organization/') &&
                resp.request().method() === 'POST' &&
                resp.status() === 201,
            ),
            authenticatedPage.locator('#create-org-confirm').click(),
          ]);

          await expect(
            authenticatedPage.locator('#create-org-cancel'),
          ).not.toBeVisible({timeout: 10000});

          // Go to settings — email should be empty
          await authenticatedPage.goto(
            `/organization/${orgName}?tab=Settings`,
          );
          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toHaveValue('');

          // Add email and save
          await emailInput.fill(addedEmail);
          await authenticatedPage.locator('#save-org-settings').click();
          await expect(
            authenticatedPage.getByText('Successfully updated settings').first(),
          ).toBeVisible();

          // Reload and verify persistence
          await authenticatedPage.reload();
          await expect(emailInput).toHaveValue(addedEmail);

          // Clean up
          await api.raw.deleteOrganization(orgName);
        });

        test('internal UUID email is never exposed in the UI', async ({
          authenticatedPage,
          api,
        }) => {
          const org = await api.organization(
            'uuidcheck',
            'visible@example.com',
          );

          // Check settings page
          await authenticatedPage.goto(
            `/organization/${org.name}?tab=Settings`,
          );
          const emailInput = authenticatedPage.locator('#org-settings-email');
          await expect(emailInput).toBeVisible();

          const value = await emailInput.inputValue();
          expect(value).not.toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-/);
          expect(value).toBe('visible@example.com');
        });
      },
    );

    // =========================================================================
    // Group 4: API Contract Verification
    // =========================================================================

    test.describe('Contact Email — API Contract', () => {
      test('GET /organization/<name> returns contact_email for admin', async ({
        api,
      }) => {
        const contactEmail = 'api-get@example.com';
        const org = await api.organization('apiget', contactEmail);

        const orgData = await api.raw.getOrganization(org.name);

        expect(orgData).toHaveProperty('contact_email', contactEmail);
        // Backward compat: email field should also have the contact email
        expect(orgData).toHaveProperty('email', contactEmail);
        // email should NOT be a UUID
        expect(orgData.email).not.toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-/);
      });

      test('backward compat: email field in POST still works', async ({
        authenticatedRequest,
      }) => {
        const orgName = uniqueName('bwcompat');
        const email = `${orgName}@example.com`;

        // POST with old-style `email` field (not contact_email)
        const token = await (async () => {
          const resp = await authenticatedRequest.get(
            `${API_URL}/csrf_token`,
          );
          const data = await resp.json();
          return data.csrf_token;
        })();

        const createResp = await authenticatedRequest.post(
          `${API_URL}/api/v1/organization/`,
          {
            headers: {'X-CSRF-Token': token},
            data: {name: orgName, email},
          },
        );
        expect(createResp.status()).toBe(201);

        // GET and verify contact_email is set from the email field
        const getResp = await authenticatedRequest.get(
          `${API_URL}/api/v1/organization/${orgName}`,
        );
        const orgData = await getResp.json();
        expect(orgData.contact_email).toBe(email);
        expect(orgData.email).toBe(email);

        // Clean up
        await authenticatedRequest.delete(
          `${API_URL}/api/v1/organization/${orgName}`,
          {
            headers: {'X-CSRF-Token': token},
          },
        );
      });

      test('FEATURE_MAILING no longer blocks org creation without email', async ({
        authenticatedPage,
        api,
      }) => {
        await authenticatedPage.goto('/organization');

        const orgName = uniqueName('nomailing');

        await authenticatedPage
          .locator('#create-organization-button')
          .click();
        await authenticatedPage
          .locator('#create-org-name-input')
          .fill(orgName);

        // Leave email empty — should still be able to create
        await expect(
          authenticatedPage.locator('#create-org-confirm'),
        ).toBeEnabled();

        const [response] = await Promise.all([
          authenticatedPage.waitForResponse(
            (resp) =>
              resp.url().includes('/api/v1/organization/') &&
              resp.request().method() === 'POST',
          ),
          authenticatedPage.locator('#create-org-confirm').click(),
        ]);

        expect(response.status()).toBe(201);

        await expect(
          authenticatedPage.locator('#create-org-cancel'),
        ).not.toBeVisible({timeout: 10000});

        // No "Email address is required" error
        await expect(
          authenticatedPage.getByText('Email address is required'),
        ).not.toBeVisible();

        await expect(
          authenticatedPage.getByText(
            `Successfully created organization ${orgName}`,
          ),
        ).toBeVisible();

        // Clean up
        await api.raw.deleteOrganization(orgName);
      });
    });

    // =========================================================================
    // Group 5: Recovery Flow — Contact Email Lookup
    // =========================================================================

    test.describe('Recovery — Contact Email Lookup', () => {
      const GENERIC_RECOVERY_MESSAGE =
        'Recovery instructions have been sent to';

      test('recovery shows generic sent message for any email type', async ({
        unauthenticatedPage,
      }) => {
        await unauthenticatedPage.goto('/signin');

        // Click forgot password
        await unauthenticatedPage.getByText('Forgot password?').click();

        // Enter an arbitrary email
        await unauthenticatedPage
          .getByTestId('signin-recovery-email')
          .fill('anyemail@example.com');
        await unauthenticatedPage.getByRole('button', {name: 'Send'}).click();

        // Verify generic message (no info leak)
        await expect(
          unauthenticatedPage.getByText(GENERIC_RECOVERY_MESSAGE),
        ).toBeVisible();
      });

      test('recovery with unknown email shows same generic message', async ({
        unauthenticatedPage,
      }) => {
        await unauthenticatedPage.goto('/signin');

        await unauthenticatedPage.getByText('Forgot password?').click();
        await unauthenticatedPage
          .getByTestId('signin-recovery-email')
          .fill('nonexistent-xyz-999@nowhere.test');
        await unauthenticatedPage.getByRole('button', {name: 'Send'}).click();

        // Same generic message — no information leak about account existence
        await expect(
          unauthenticatedPage.getByText(GENERIC_RECOVERY_MESSAGE),
        ).toBeVisible();
      });
    });
  },
);
