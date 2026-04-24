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

    test('build with invalid Dockerfile shows error state', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('builderror');
      const repo = await api.repository(org.name, 'build-error');

      // Trigger a build with invalid Dockerfile content
      const build = await api.build(
        org.name,
        repo.name,
        'INVALID DOCKERFILE CONTENT\n',
      );

      // Wait for build to reach terminal phase (should error)
      const result = await api.raw.waitForBuildPhase(
        org.name,
        repo.name,
        build.buildId,
      );

      expect(['error', 'internal_error']).toContain(result.phase);

      // Navigate to builds tab and verify error is shown
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await expect(
        authenticatedPage.getByText(build.buildId.substring(0, 8)),
      ).toBeVisible();
    });

    test('shows empty state when no builds exist', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nobilds');
      const repo = await api.repository(org.name, 'empty-builds');

      // Navigate to Builds tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      // Should show empty state
      await expect(
        authenticatedPage.getByText('No builds have been run'),
      ).toBeVisible();
    });
  },
);
