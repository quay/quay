import {test, expect} from '../../fixtures';

test.describe(
  'Build History',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    test('displays build history table with correct columns', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldhistcol');
      const repo = await api.repository(org.name, 'histcol-repo');
      await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await expect(
        authenticatedPage.getByRole('heading', {name: 'Build History'}),
      ).toBeVisible();

      const table = authenticatedPage.getByRole('table', {
        name: 'Repository builds table',
      });
      await expect(table).toBeVisible();
      await expect(
        table.getByRole('columnheader', {name: 'Build ID'}),
      ).toBeVisible();
      await expect(
        table.getByRole('columnheader', {name: 'Status'}),
      ).toBeVisible();
      await expect(
        table.getByRole('columnheader', {name: 'Triggered by'}),
      ).toBeVisible();
      await expect(
        table.getByRole('columnheader', {name: 'Date started'}),
      ).toBeVisible();
      await expect(
        table.getByRole('columnheader', {name: 'Tags'}),
      ).toBeVisible();
    });

    test('displays empty state when no builds exist', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldempty');
      const repo = await api.repository(org.name, 'empty-repo');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await expect(
        authenticatedPage.getByText(
          'No matching builds found. Please start a new build or adjust filter to view build status.',
        ),
      ).toBeVisible();
    });

    test('build row links to build detail page', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldlink');
      const repo = await api.repository(org.name, 'link-repo');
      const build = await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      const row = authenticatedPage.getByTestId(`row-${build.buildId}`);
      await expect(row).toBeVisible();

      const buildLink = row.locator('[data-label="Build ID"] a');
      await expect(buildLink).toBeVisible();
      await buildLink.click();

      await expect(authenticatedPage).toHaveURL(
        new RegExp(
          `/repository/${org.name}/${repo.name}/build/${build.buildId}`,
        ),
      );
    });

    test('date filter toggles switch correctly', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldfilter');
      const repo = await api.repository(org.name, 'filter-repo');
      await api.build(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      const recentBtn = authenticatedPage.getByRole('button', {
        name: 'filter recent builds',
      });
      const last48Btn = authenticatedPage.getByRole('button', {
        name: 'filter builds from last 48 hours',
      });
      const last30Btn = authenticatedPage.getByRole('button', {
        name: 'filter builds from last 30 days',
      });

      await expect(recentBtn).toBeVisible();
      await expect(last48Btn).toBeVisible();
      await expect(last30Btn).toBeVisible();

      await expect(recentBtn).toHaveAttribute('aria-pressed', 'true');

      await last48Btn.click();
      await expect(last48Btn).toHaveAttribute('aria-pressed', 'true');
      await expect(recentBtn).toHaveAttribute('aria-pressed', 'false');

      await last30Btn.click();
      await expect(last30Btn).toHaveAttribute('aria-pressed', 'true');
      await expect(last48Btn).toHaveAttribute('aria-pressed', 'false');
    });

    test('Start New Build button visible for write-access users', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldstartbtn');
      const repo = await api.repository(org.name, 'startbtn-repo');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await expect(
        authenticatedPage.getByRole('button', {name: 'Start New Build'}),
      ).toBeVisible();
    });

    test('Start New Build modal opens with two tabs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldmodal');
      const repo = await api.repository(org.name, 'modal-repo');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await authenticatedPage
        .getByRole('button', {name: 'Start New Build'})
        .click();

      const modal = authenticatedPage.locator('#start-build-modal');
      await expect(modal).toBeVisible();
      await expect(modal.getByText('Start Repository Build')).toBeVisible();
      await expect(
        modal.getByRole('tab', {name: 'invoke build trigger tab'}),
      ).toBeVisible();
      await expect(
        modal.getByRole('tab', {name: 'upload dockerfile tab'}),
      ).toBeVisible();

      // No triggers → empty message
      await expect(
        modal.getByText('No build triggers available for this repository.'),
      ).toBeVisible();

      // Cancel closes modal
      await modal.getByRole('button', {name: 'Cancel'}).click();
      await expect(modal).not.toBeVisible();
    });

    test('build triggers section renders with empty state', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldtrigempty');
      const repo = await api.repository(org.name, 'trigempty-repo');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      await expect(
        authenticatedPage.getByRole('heading', {name: 'Build Triggers'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'No build triggers defined. Build triggers invoke builds whenever the triggered condition is met (source control push, webhook, etc)',
        ),
      ).toBeVisible();
    });

    test('create trigger dropdown is visible', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('bldtrigdd');
      const repo = await api.repository(org.name, 'trigdd-repo');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=builds`,
      );

      const dropdown = authenticatedPage.getByTestId('create-trigger-dropdown');
      await expect(dropdown).toBeVisible();

      await dropdown.click();
      await expect(
        authenticatedPage.getByText('Custom Git Repository Push'),
      ).toBeVisible();
    });
  },
);
