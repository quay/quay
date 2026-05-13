import {test, expect} from '../../fixtures';

test.describe(
  'Build Detail Page',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    test('displays build information card', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('blddetinfo');
      const repo = await api.repository(org.name, 'detinfo-repo');
      const build = await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
      );

      const infoCard = authenticatedPage.locator(
        '[data-ouia-component-id="build-info-card"]',
      );
      await expect(infoCard).toBeVisible();
      await expect(infoCard.getByText('Build Information')).toBeVisible();

      // Build ID field
      const buildIdGroup = infoCard.locator('#build-id');
      await expect(buildIdGroup).toBeVisible();
      await expect(buildIdGroup.getByText('Build ID')).toBeVisible();
      await expect(buildIdGroup).toContainText(build.buildId);

      // Triggered by field
      const triggeredByGroup = infoCard.locator('#triggered-by');
      await expect(triggeredByGroup).toBeVisible();
      await expect(triggeredByGroup.getByText('Triggered by')).toBeVisible();

      // Status field
      const statusGroup = infoCard.locator('#status');
      await expect(statusGroup).toBeVisible();
      await expect(statusGroup.getByText('Status')).toBeVisible();

      // Started field
      const startedGroup = infoCard.locator('#started');
      await expect(startedGroup).toBeVisible();
      await expect(startedGroup.getByText('Started')).toBeVisible();
    });

    test('displays build logs card with action buttons', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('blddetlogs');
      const repo = await api.repository(org.name, 'detlogs-repo');
      const build = await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
      );

      const logsCard = authenticatedPage.locator(
        '[data-ouia-component-id="build-logs-card"]',
      );
      await expect(logsCard).toBeVisible();
      await expect(logsCard.getByText('Build Logs')).toBeVisible();

      // Build logs container
      await expect(authenticatedPage.locator('#build-logs')).toBeVisible();

      // Show timestamps button
      const timestampBtn = authenticatedPage.locator(
        '#toggle-timestamps-button',
      );
      await expect(timestampBtn).toBeVisible();
      await expect(timestampBtn).toContainText('Show timestamps');

      // Toggle timestamps
      await timestampBtn.click();
      await expect(timestampBtn).toContainText('Hide timestamps');

      await timestampBtn.click();
      await expect(timestampBtn).toContainText('Show timestamps');
    });

    test('copy button is present in build logs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('blddetcopy');
      const repo = await api.repository(org.name, 'detcopy-repo');
      const build = await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
      );

      const logsCard = authenticatedPage.locator(
        '[data-ouia-component-id="build-logs-card"]',
      );
      await expect(logsCard).toBeVisible();
      await expect(logsCard.getByRole('button', {name: 'Copy'})).toBeVisible();
    });

    test('navigates back to builds tab from build detail', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('blddetback');
      const repo = await api.repository(org.name, 'detback-repo');
      const build = await api.build(org.name, repo.name);

      // Navigate to builds tab first, then click into detail
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      const row = authenticatedPage.getByTestId(`row-${build.buildId}`);
      await expect(row).toBeVisible();
      await row.locator('[data-label="Build ID"] a').click();

      await expect(authenticatedPage).toHaveURL(
        new RegExp(`/build/${build.buildId}`),
      );

      // Navigate back
      await authenticatedPage.goBack();
      await expect(authenticatedPage).toHaveURL(
        new RegExp(`/repository/${org.name}/${repo.name}.*tab=builds`),
      );
    });

    test('shows manually triggered build description', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('blddetmanual');
      const repo = await api.repository(org.name, 'detmanual-repo');
      const build = await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
      );

      const triggeredByGroup = authenticatedPage.locator('#triggered-by');
      await expect(triggeredByGroup).toBeVisible();
      await expect(triggeredByGroup).toContainText(
        /Manually started build|testuser/,
      );
    });
  },
);
