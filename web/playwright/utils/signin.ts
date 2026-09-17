import {expect, type Page} from '@playwright/test';
import {isServiceMode} from './config';

const SERVICE_SIGNIN_TEXT = /Log in to your (Red Hat )?account|Red Hat login/i;

export async function expectSigninPageForTarget(
  page: Page,
  options: {localAngularShell?: boolean} = {},
): Promise<void> {
  if (isServiceMode()) {
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('body')).toContainText(SERVICE_SIGNIN_TEXT);
    return;
  }

  if (options.localAngularShell) {
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached();
  }

  await expect(
    page
      .locator('input[name="username"]')
      .or(page.getByRole('textbox', {name: /username/i}))
      .first(),
  ).toBeVisible({timeout: 10000});
  await expect(
    page
      .locator('input[name="password"]')
      .or(page.getByLabel(/password/i))
      .first(),
  ).toBeVisible({timeout: 10000});
}
