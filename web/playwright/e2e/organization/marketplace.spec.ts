import {type Page} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

const marketplaceOrgResponse = [
  {
    id: 1,
    subscription_id: 12345678,
    user_id: 36,
    org_id: 37,
    quantity: 2,
    sku: 'MW02701',
    metadata: {
      title: 'premium',
      privateRepos: 9007199254740991,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02701',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
];

const marketplaceUnlimitedResponse = [
  {
    id: 1,
    subscription_id: 12345678,
    user_id: 36,
    org_id: 37,
    quantity: 2,
    sku: 'MW02702',
    metadata: {
      title: 'premium',
      privateRepos: 9007199254740991,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02702',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
];

const marketplaceUserResponse = [
  {
    id: 12345678,
    masterEndSystemName: 'Quay',
    createdEndSystemName: 'SUBSCRIPTION',
    createdDate: 1675957362000,
    lastUpdateEndSystemName: 'SUBSCRIPTION',
    lastUpdateDate: 1675957362000,
    installBaseStartDate: 1707368400000,
    installBaseEndDate: 1707368399000,
    webCustomerId: 123456,
    subscriptionNumber: '12399889',
    quantity: 2,
    effectiveStartDate: 1707368400000,
    effectiveEndDate: 3813177600,
    sku: 'MW02701',
    assigned_to_org: null,
    metadata: {
      title: 'premium',
      privateRepos: 100,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02701',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
  {
    id: 11223344,
    masterEndSystemName: 'Quay',
    createdEndSystemName: 'SUBSCRIPTION',
    createdDate: 1675957362000,
    lastUpdateEndSystemName: 'SUBSCRIPTION',
    lastUpdateDate: 1675957362000,
    installBaseStartDate: 1707368400000,
    installBaseEndDate: 1707368399000,
    webCustomerId: 123456,
    subscriptionNumber: '12399889',
    quantity: 1,
    effectiveStartDate: 1707368400000,
    effectiveEndDate: 3813177600,
    sku: 'MW02701',
    assigned_to_org: null,
    metadata: {
      title: 'premium',
      privateRepos: 100,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02701',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
];

const plansResponse = {
  hasSubscription: false,
  isExistingCustomer: true,
  plan: 'free',
  usedPrivateRepos: 0,
};

const privateResponse = {
  privateAllowed: true,
  privateCount: 0,
};

async function enableMarketplace(page: Page): Promise<void> {
  await page.route('**/config', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.features.BILLING = true;
    body.features.RH_MARKETPLACE = true;
    await route.fulfill({response, body: JSON.stringify(body)});
  });
}

test.describe('Marketplace Subscriptions', {tag: ['@marketplace']}, () => {
  test('lists user marketplace subscriptions', async ({authenticatedPage}) => {
    const username = TEST_USERS.user.username;

    await enableMarketplace(authenticatedPage);
    await authenticatedPage.route(
      '**/api/v1/user/marketplace',
      async (route) => {
        await route.fulfill({json: marketplaceUserResponse});
      },
    );
    await authenticatedPage.route('**/api/v1/user/private', async (route) => {
      await route.fulfill({json: privateResponse});
    });
    await authenticatedPage.route('**/api/v1/user/plan', async (route) => {
      await route.fulfill({json: plansResponse});
    });

    await authenticatedPage.goto(`/organization/${username}?tab=Settings`);
    await authenticatedPage.getByText('Billing information').click();

    const subscriptionList = authenticatedPage.locator(
      '#user-subscription-list',
    );
    await expect(
      subscriptionList.getByText('2x MW02701 belonging to user namespace'),
    ).toBeVisible();
    await expect(
      subscriptionList.getByText('1x MW02701 belonging to user namespace'),
    ).toBeVisible();
  });

  test('attaches and removes org marketplace subscriptions', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('mktplace');

    await enableMarketplace(authenticatedPage);
    await authenticatedPage.route('**/api/v1/plans', async (route) => {
      await route.fulfill({json: []});
    });
    await authenticatedPage.route('**/api/v1/user/private', async (route) => {
      await route.fulfill({json: privateResponse});
    });
    await authenticatedPage.route('**/api/v1/user/plan', async (route) => {
      await route.fulfill({json: plansResponse});
    });
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/plan`,
      async (route) => {
        await route.fulfill({json: plansResponse});
      },
    );
    await authenticatedPage.route(
      '**/api/v1/user/marketplace',
      async (route) => {
        await route.fulfill({json: marketplaceUserResponse});
      },
    );
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/marketplace/batchremove`,
      async (route) => {
        await route.fulfill({status: 200, body: 'Okay'});
      },
    );
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/marketplace`,
      async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({status: 200, body: 'Okay'});
        } else {
          await route.fulfill({json: marketplaceOrgResponse});
        }
      },
    );

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
    await authenticatedPage.getByText('Billing information').click();

    // Attach subscription
    await authenticatedPage.locator('#attach-subscription-button').click();
    await authenticatedPage.locator('#subscription-select-toggle').click();
    await authenticatedPage
      .locator('#subscription-select-list')
      .getByText('2x MW02701')
      .click();
    await authenticatedPage.locator('#confirm-subscription-select').click();
    await expect(
      authenticatedPage.getByText('Successfully attached subscription'),
    ).toBeVisible();

    // Remove subscription
    await authenticatedPage.locator('#remove-subscription-button').click();
    await authenticatedPage.locator('#subscription-select-toggle').click();
    await authenticatedPage
      .locator('#subscription-select-list')
      .getByText('2x MW02701')
      .click();
    await authenticatedPage.locator('#confirm-subscription-select').click();
    await expect(
      authenticatedPage.getByText('Successfully removed subscription'),
    ).toBeVisible();
  });

  test('shows unlimited private repos for unlimited subscription SKU', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('mktunlim');

    await enableMarketplace(authenticatedPage);
    await authenticatedPage.route('**/api/v1/plans', async (route) => {
      await route.fulfill({json: []});
    });
    await authenticatedPage.route('**/api/v1/user/private', async (route) => {
      await route.fulfill({json: privateResponse});
    });
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/private`,
      async (route) => {
        await route.fulfill({json: privateResponse});
      },
    );
    await authenticatedPage.route('**/api/v1/user/plan', async (route) => {
      await route.fulfill({json: plansResponse});
    });
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/plan`,
      async (route) => {
        await route.fulfill({json: plansResponse});
      },
    );
    await authenticatedPage.route(
      '**/api/v1/user/marketplace',
      async (route) => {
        await route.fulfill({json: marketplaceUserResponse});
      },
    );
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/marketplace`,
      async (route) => {
        await route.fulfill({json: marketplaceUnlimitedResponse});
      },
    );

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
    await authenticatedPage.getByText('Billing information').click();

    await expect(
      authenticatedPage
        .locator('#form-form')
        .getByText('0 of unlimited private repositories used'),
    ).toBeVisible();
  });
});
