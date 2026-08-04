import {test, expect} from '../../fixtures';

test.describe('Footer', {tag: ['@ui']}, () => {
  test('renders footer structure', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/organization');

    await expect(authenticatedPage.locator('#quay-footer')).toBeVisible();
    await expect(
      authenticatedPage.locator('.quay-footer-container'),
    ).toBeVisible();
    await expect(authenticatedPage.locator('.quay-footer-list')).toBeVisible();
  });

  test('footer is visible on multiple pages', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/organization');
    await expect(authenticatedPage.locator('#quay-footer')).toBeVisible();

    await authenticatedPage.goto('/repository');
    await expect(authenticatedPage.locator('#quay-footer')).toBeVisible();
  });

  test('quay.io: TrustArc and consent elements are present', async ({
    authenticatedPage,
    quayConfig,
  }) => {
    const serverHostname = quayConfig?.config?.SERVER_HOSTNAME as
      | string
      | undefined;
    const isQuayIO =
      serverHostname === 'quay.io' || serverHostname === 'stage.quay.io';
    test.skip(!isQuayIO, 'Only applies to quay.io / stage.quay.io deployments');

    await authenticatedPage.goto('/organization');

    // #consent_blackbar renders for any quay.io deployment
    await expect(authenticatedPage.locator('#consent_blackbar')).toBeVisible();

    // TrustArc widget renders only when BILLING is also enabled;
    // use toHaveCount to avoid flaking on async external script load
    if (quayConfig?.features?.BILLING) {
      await expect(authenticatedPage.locator('#teconsent')).toHaveCount(1);
    }
  });

  test('non-quay.io: no TrustArc or service status icon', async ({
    authenticatedPage,
    quayConfig,
  }) => {
    const serverHostname = quayConfig?.config?.SERVER_HOSTNAME as
      | string
      | undefined;
    const isQuayIO =
      serverHostname === 'quay.io' || serverHostname === 'stage.quay.io';
    test.skip(isQuayIO, 'Only applies to non-quay.io deployments');

    await authenticatedPage.goto('/organization');

    await expect(
      authenticatedPage.locator('.service-status-icon'),
    ).not.toBeVisible();
    await expect(authenticatedPage.locator('#teconsent')).not.toBeVisible();
    await expect(
      authenticatedPage.locator('#consent_blackbar'),
    ).not.toBeVisible();
  });
});
