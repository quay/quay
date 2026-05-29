/**
 * Service Status (StatusPage Integration) Tests (PROJQUAY-11629)
 *
 * Tests the RegistryStatus component that displays service incidents
 * and maintenance windows from the StatusPage API.
 *
 * Uses page.route() for the external StatusPage CDN script (acceptable
 * for external services per no-mocks policy) and page.addInitScript()
 * to inject the mock StatusPage library.
 */

import {test as base, expect} from '../../fixtures';

const test = base;

const STATUS_DATA = {
  components: [
    {
      id: 'cllr1k2dzsf7',
      name: 'Quay.io',
      status: 'major_outage',
      group: true,
      components: ['m65lxn2nf6l0', '6fb8zflt4fbt'],
    },
    {
      id: 'm65lxn2nf6l0',
      name: 'API',
      status: 'major_outage',
      group: false,
      group_id: 'cllr1k2dzsf7',
    },
    {
      id: '6fb8zflt4fbt',
      name: 'Build System',
      status: 'partial_outage',
      group: false,
      group_id: 'cllr1k2dzsf7',
    },
  ],
  incidents: [
    {
      name: 'incident1',
      shortlink: 'https://stspg.io/incident1',
      components: [{id: 'm65lxn2nf6l0'}, {id: '6fb8zflt4fbt'}],
    },
    {
      name: 'incident2',
      shortlink: 'https://stspg.io/incident2',
      components: [{id: 'm65lxn2nf6l0'}, {id: '6fb8zflt4fbt'}],
    },
  ],
  scheduled_maintenances: [
    {
      status: 'scheduled',
      name: 'maintenance1',
      shortlink: 'https://stspg.io/maintenance1',
      components: [{id: 'm65lxn2nf6l0'}, {id: '6fb8zflt4fbt'}],
      scheduled_for: '2024-02-09T10:00:00.000-05:00',
    },
    {
      status: 'in_progress',
      name: 'maintenance2',
      shortlink: 'https://stspg.io/maintenance2',
      components: [{id: 'm65lxn2nf6l0'}, {id: '6fb8zflt4fbt'}],
      scheduled_for: '2024-02-09T10:00:00.000-05:00',
    },
  ],
};

async function setupServiceStatusMock(
  page: import('@playwright/test').Page,
  data: typeof STATUS_DATA,
) {
  await page.route('**/config', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.features = {...body.features, BILLING: true};
    await route.fulfill({response, body: JSON.stringify(body)});
  });

  await page.route('**/cdn.statuspage.io/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: '// mocked StatusPage CDN script',
    });
  });

  await page.addInitScript((statusData) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as unknown as Record<string, unknown>).StatusPage = {
      page: class {
        summary(callbacks: {success: (d: unknown) => void}) {
          setTimeout(() => callbacks.success(statusData), 0);
        }
      },
    };
  }, data);
}

test.describe('Service Status', {tag: ['@ui', '@PROJQUAY-11629']}, () => {
  test('displays incidents and maintenances', async ({userContext}) => {
    const page = await userContext.newPage();
    await setupServiceStatusMock(page, STATUS_DATA);

    await page.goto('/organization');

    const incident1 = page.getByRole('link', {name: 'incident1'});
    await expect(incident1).toBeVisible();
    await expect(incident1).toHaveAttribute(
      'href',
      'https://stspg.io/incident1',
    );

    const incident2 = page.getByRole('link', {name: 'incident2'});
    await expect(incident2).toBeVisible();
    await expect(incident2).toHaveAttribute(
      'href',
      'https://stspg.io/incident2',
    );

    await expect(page.getByText(/Scheduled for/)).toBeVisible();
    const maintenance1 = page.getByRole('link', {name: 'maintenance1'});
    await expect(maintenance1).toBeVisible();
    await expect(maintenance1).toHaveAttribute(
      'href',
      'https://stspg.io/maintenance1',
    );

    await expect(page.getByText('In progress:')).toBeVisible();
    const maintenance2 = page.getByRole('link', {name: 'maintenance2'});
    await expect(maintenance2).toBeVisible();
    await expect(maintenance2).toHaveAttribute(
      'href',
      'https://stspg.io/maintenance2',
    );

    await page.close();
  });

  test('hides status section when no incidents or maintenances exist', async ({
    userContext,
  }) => {
    const emptyData = {
      ...STATUS_DATA,
      incidents: [] as typeof STATUS_DATA.incidents,
      scheduled_maintenances: [] as typeof STATUS_DATA.scheduled_maintenances,
    };

    const page = await userContext.newPage();
    await setupServiceStatusMock(page, emptyData);

    await page.goto('/organization');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('#registry-status')).not.toBeAttached();

    await page.close();
  });
});
