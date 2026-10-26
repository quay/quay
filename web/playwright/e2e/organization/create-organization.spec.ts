import {test, expect, uniqueName} from '../../fixtures/isolated-account';
import {selectFreeOrganizationPlan} from '../../utils/organization-creation';
import type {Plan} from '../../../src/resources/BillingResource';

test.describe('Create Organization page', {tag: ['@organization']}, () => {
  test('creation opens in the current page and offers the organization plan catalog', async ({
    authenticatedPage: page,
    quayConfig,
  }) => {
    const pages = page.context().pages().length;
    await page.goto('/organization');
    await page.getByRole('button', {name: 'Create Organization'}).click();
    await expect(page).toHaveURL(/\/organizations\/new$/);
    await expect(
      page.getByRole('heading', {name: 'Create Organization'}),
    ).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.locator('#create-org-confirm')).toBeDisabled();
    expect(page.context().pages()).toHaveLength(pages);
    if (quayConfig.features.BILLING) {
      const response = await page.request.get('/api/v1/plans/');
      expect(response.ok()).toBe(true);
      const {plans}: {plans: Plan[]} = await response.json();
      const eligible = plans.filter(
        (plan) =>
          !plan.deprecated &&
          !plan.plans_page_hidden &&
          (plan.stripeId === 'free' || plan.bus_features),
      );
      await expect(page.getByRole('radio')).toHaveCount(eligible.length);
      for (const plan of eligible) {
        await expect(
          page.locator(`[id="organization-plan-${plan.stripeId}"]`),
        ).toBeVisible();
      }
    } else {
      await expect(page.getByRole('radio')).toHaveCount(0);
    }
    await page.setViewportSize({width: 1440, height: 1200});
    await page.screenshot({
      path: test.info().outputPath('create-organization-desktop.png'),
      fullPage: true,
    });
    await page.setViewportSize({width: 390, height: 844});
    await page.getByRole('button', {name: 'Global navigation'}).click();
    await expect(page.locator('#create-org-name-input')).toBeVisible();
    await expect(page.locator('#create-org-confirm')).toBeVisible();
    await page.screenshot({
      path: test.info().outputPath('create-organization-mobile.png'),
    });
    await page.locator('#create-org-confirm').scrollIntoViewIfNeeded();
    await expect(page.locator('#create-org-confirm')).toBeInViewport();
    await page.screenshot({
      path: test.info().outputPath('create-organization-mobile-plans.png'),
    });
  });

  test('validates names and email before allowing creation', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/organizations/new');
    const name = page.locator('#create-org-name-input');
    const submit = page.locator('#create-org-confirm');
    await selectFreeOrganizationPlan(page);
    for (const invalid of ['a', 'MyOrg', 'invalid name']) {
      await name.fill(invalid);
      await expect(submit).toBeDisabled();
    }
    await name.fill('ab');
    await expect(
      page.getByText(
        'Namespaces less than 4 or more than 30 characters are only compatible with Docker 1.6+',
      ),
    ).toBeVisible();
    await name.fill('my-org');
    await expect(
      page.getByText(
        'Namespaces with dashes or dots are only compatible with Docker 1.9+',
      ),
    ).toBeVisible();
    await name.fill('validorg');
    await expect(submit).toBeEnabled();
    await page.locator('#create-org-email-input').fill('invalid-email');
    await name.click();
    await expect(
      page.getByText('Enter a valid email: email@provider.com'),
    ).toBeVisible();
    await expect(submit).toBeDisabled();
    await page.locator('#create-org-email-input').fill('org@example.com');
    await expect(submit).toBeEnabled();
  });

  test('creates a free organization once and navigates to it without checkout', async ({
    authenticatedPage: page,
    api,
    quayConfig,
  }) => {
    const name = uniqueName('freeorg');
    const writes: string[] = [];
    page.on('request', (request) => {
      if (
        request.method() === 'POST' &&
        new URL(request.url()).pathname.startsWith('/api/v1/organization/')
      )
        writes.push(new URL(request.url()).pathname);
    });
    await page.goto('/organizations/new/');
    await page.locator('#create-org-name-input').fill(name);
    if (quayConfig.features.BILLING)
      await expect(page.locator('#create-org-confirm')).toBeDisabled();
    await selectFreeOrganizationPlan(page);
    try {
      const response = page.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === '/api/v1/organization/' &&
          response.request().method() === 'POST',
      );
      // Two synchronous submissions must still create only one organization.
      await page
        .locator('#create-org-confirm')
        .evaluate((button: HTMLButtonElement) => {
          button.click();
          button.click();
        });
      expect((await response).status()).toBe(201);
      await expect(page).toHaveURL(new RegExp(`/organization/${name}$`));
      await expect(
        page.getByText(`Successfully created organization ${name}`),
      ).toBeVisible();
      await expect(
        page
          .locator('.pf-v6-c-alert')
          .filter({hasText: `Successfully created organization ${name}`}),
      ).toHaveAttribute('aria-live', 'polite');
      expect(writes).toEqual(['/api/v1/organization/']);
      const org = await api.raw.getOrganization(name);
      expect(org.name).toBe(name);
    } finally {
      await api.raw.deleteOrganization(name);
    }
  });

  test('cancel returns to the list without creating an organization', async ({
    authenticatedPage: page,
  }) => {
    const writes: string[] = [];
    page.on('request', (request) => {
      if (request.method() === 'POST') writes.push(request.url());
    });
    await page.goto('/organizations/new');
    await page.locator('#create-org-name-input').fill('nevercreated');
    await page.locator('#create-org-cancel').click();
    await expect(page).toHaveURL(/\/organization$/);
    expect(writes).toEqual([]);
  });

  test('an existing organization name preserves input and never starts checkout', async ({
    authenticatedPage: page,
    api,
    quayConfig,
  }) => {
    const existing = await api.organization('existing');
    const checkouts: string[] = [];
    page.on('request', (request) => {
      if (
        request.method() === 'POST' &&
        new URL(request.url()).pathname.endsWith('/plan')
      )
        checkouts.push(request.url());
    });
    await page.goto('/organizations/new');
    await page.locator('#create-org-name-input').fill(existing.name);
    if (quayConfig.features.BILLING) {
      // The last catalog row is a business plan.
      await expect(page.getByRole('radio').last()).toBeVisible();
      await page.getByRole('radio').last().check();
    }
    const response = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === '/api/v1/organization/' &&
        response.request().method() === 'POST',
    );
    await page.locator('#create-org-confirm').click();
    expect((await response).status()).toBe(400);
    await expect(page.getByTestId('create-organization-error')).toHaveAttribute(
      'aria-live',
      'polite',
    );
    await expect(
      page.getByRole('heading', {name: /Unable to create organization/}),
    ).toBeVisible();
    await expect(page.locator('#create-org-name-input')).toHaveValue(
      existing.name,
    );
    await expect(page.locator('#create-org-confirm')).toBeEnabled();
    expect(checkouts).toEqual([]);
  });

  test(
    'paid checkout failure can retry without recreating the organization',
    {tag: ['@billing', '@feature:BILLING']},
    async ({authenticatedPage: page, api, baseURL}) => {
      test.skip(
        process.env.PLAYWRIGHT_BILLING_EXPECT_CHECKOUT_ERROR !== 'true',
        'Requires an explicitly selected backend where checkout is unavailable.',
      );
      const name = uniqueName('paidorg');
      const writes: string[] = [];
      const pageCount = page.context().pages().length;
      page.on('request', (request) => {
        if (
          request.method() === 'POST' &&
          new URL(request.url()).pathname.startsWith('/api/v1/organization/')
        )
          writes.push(new URL(request.url()).pathname);
      });
      await page.goto('/organizations/new');
      const catalog = await page.request.get('/api/v1/plans/');
      const {plans}: {plans: Plan[]} = await catalog.json();
      const plan = plans.find(
        (entry) =>
          entry.bus_features &&
          entry.price > 0 &&
          !entry.deprecated &&
          !entry.plans_page_hidden,
      );
      expect(plan).toBeDefined();
      await page.locator('#create-org-name-input').fill(name);
      await page.locator('#create-org-email-input').fill(`${name}@example.com`);
      await page.locator(`[id="organization-plan-${plan.stripeId}"]`).check();
      const endpoint = `/api/v1/organization/${name}/plan`;
      const checkoutResponse = () =>
        page.waitForResponse(
          (response) =>
            new URL(response.url()).pathname === endpoint &&
            response.request().method() === 'POST',
        );
      try {
        const firstCheckout = checkoutResponse();
        await page
          .getByRole('button', {name: 'Create and continue to checkout'})
          .click();
        const response = await firstCheckout;
        expect(response.status()).toBeGreaterThanOrEqual(400);
        const request = response.request();
        expect(!!request.headers()['x-csrf-token']).toBe(true);
        expect(!!request.headers().authorization).toBe(false);
        const body = request.postDataJSON();
        expect(body.plan).toBe(plan.stripeId);
        for (const [field, result] of [
          ['success_url', 'returned'],
          ['cancel_url', 'canceled'],
        ]) {
          const url = new URL(body[field]);
          expect(url.origin).toBe(new URL(baseURL).origin);
          expect(url.pathname).toBe(`/organization/${name}`);
          expect(url.searchParams.get('planCheckout')).toBe(result);
          expect(url.searchParams.get('checkoutPlan')).toBe(plan.stripeId);
        }
        await expect(
          page.getByRole('heading', {
            name: /Organization created; payment setup could not be started/,
          }),
        ).toBeVisible();
        await expect(page.locator('#create-org-name-input')).toBeDisabled();
        await expect(page.getByRole('radio', {checked: true})).toBeDisabled();
        const retry = checkoutResponse();
        await page.getByRole('button', {name: 'Retry checkout'}).click();
        expect((await retry).status()).toBeGreaterThanOrEqual(400);
        await expect(
          page.getByRole('button', {name: 'Retry checkout'}),
        ).toBeEnabled();
        expect(writes).toEqual(['/api/v1/organization/', endpoint, endpoint]);
        expect(page.context().pages()).toHaveLength(pageCount);
        await expect(page).toHaveURL(/\/organizations\/new$/);
        await page.getByRole('button', {name: 'Go to organization'}).click();
        await expect(page).toHaveURL(new RegExp(`/organization/${name}$`));
        await page.goto(body.cancel_url);
        await expect(
          page.getByRole('heading', {name: /Stripe Checkout canceled/}),
        ).toBeVisible();
        await expect(
          page.getByRole('link', {name: 'Choose a plan', exact: true}),
        ).toBeVisible();
        const subscription = await page.request.get(endpoint);
        expect((await subscription.json()).hasSubscription).toBe(false);
      } finally {
        await api.raw.deleteOrganization(name);
      }
    },
  );
});
