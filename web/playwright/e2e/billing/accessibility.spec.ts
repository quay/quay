import AxeBuilder from '@axe-core/playwright';
import type {Page} from '@playwright/test';
import {test, expect} from '../../fixtures/isolated-account';
import type {Plan} from '../../../src/resources/BillingResource';

async function scan(page: Page, selector: string) {
  await page.locator(selector).evaluate(async (element) => {
    await Promise.all(
      element
        .getAnimations({subtree: true})
        .filter(
          (animation) =>
            animation.effect?.getComputedTiming().iterations !== Infinity,
        )
        .map((animation) => animation.finished.catch(() => undefined)),
    );
  });
  const results = await new AxeBuilder({page})
    .include(selector)
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  await test.info().attach('accessibility-scan', {
    body: JSON.stringify(results, null, 2),
    contentType: 'application/json',
  });
  expect(results.violations).toEqual([]);
}

test.describe(
  'Billing accessibility',
  {tag: ['@organization', '@billing', '@feature:BILLING']},
  () => {
    test('announces an invalid simulated checkout session', async ({
      billingPage: page,
    }) => {
      test.skip(
        process.env.PLAYWRIGHT_FAKE_CHECKOUT !== 'true',
        'Requires the local FakeStripe provider.',
      );
      await page.goto('/fake-checkout?session=invalid-session');
      const error = page
        .getByTestId('fake-checkout-page')
        .locator('.pf-v6-c-alert')
        .filter({hasText: 'Unable to load simulated checkout'});
      await expect(error).toBeVisible();
      await expect(error).toHaveAttribute('aria-live', 'polite');
      await expect(
        page.getByRole('button', {name: 'Complete simulated checkout'}),
      ).toHaveCount(0);
    });
    test('labels organization validation and supports keyboard plan selection at desktop and 320px', async ({
      billingPage: page,
    }) => {
      await page.goto('/organizations/new');
      const name = page.getByRole('textbox', {name: 'Organization Name'});
      await expect(name).toHaveAccessibleDescription(
        /namespace for your repositories/,
      );
      await name.fill('Invalid Name');
      await expect(name).toHaveAttribute('aria-invalid', 'true');
      await expect(name).toHaveAccessibleDescription(/all lowercase/);
      await name.fill('validname');
      const email = page.getByRole('textbox', {name: 'Email (Optional)'});
      await email.fill('invalid');
      await email.press('Tab');
      await expect(email).toHaveAttribute('aria-invalid', 'true');
      await expect(email).toHaveAccessibleDescription(/Enter a valid email/);
      await email.fill('');
      const group = page.getByRole('radiogroup', {
        name: "Choose your organization's plan",
      });
      await expect(group).toHaveAttribute('aria-required', 'true');
      const radios = group.getByRole('radio');
      await radios.first().focus();
      await page.keyboard.press('Space');
      await page.keyboard.press('ArrowDown');
      await expect(radios.nth(1)).toBeChecked();
      await page.keyboard.press('ArrowUp');
      await expect(radios.first()).toBeChecked();
      await scan(page, '[data-testid="create-organization-page"]');
      await page.screenshot({
        path: test.info().outputPath('01-organization-desktop.png'),
        fullPage: true,
      });
      await page.setViewportSize({width: 320, height: 800});
      const navigation = page.getByRole('button', {name: 'Global navigation'});
      if ((await navigation.getAttribute('aria-expanded')) === 'true')
        await navigation.click();
      await name.scrollIntoViewIfNeeded();
      await expect(name).toBeInViewport();
      await scan(page, '[data-testid="create-organization-page"]');
      await test.info().attach('reflow-dom', {
        body: JSON.stringify(
          await page.evaluate(() =>
            Array.from(document.querySelectorAll('body *'))
              .filter(
                (element) =>
                  element.getBoundingClientRect().right > window.innerWidth + 1,
              )
              .slice(0, 30)
              .map((element) => ({
                tag: element.tagName,
                id: element.id,
                className: element.className,
                right: element.getBoundingClientRect().right,
                width: element.getBoundingClientRect().width,
              })),
          ),
          null,
          2,
        ),
        contentType: 'application/json',
      });
      expect(
        await page
          .getByTestId('create-organization-page')
          .evaluate((element) => element.getBoundingClientRect().right),
      ).toBeLessThanOrEqual(321);
      await page.screenshot({
        path: test.info().outputPath('02-organization-320px.png'),
        fullPage: true,
      });
    });

    test('associates the billing panel and invoice validation, and restores modal focus', async ({
      billingPage: page,
      api,
    }) => {
      const {name} = await api.organization('access');
      await page.goto(
        `/organization/${name}?tab=Settings&settingsTab=billinginformation`,
      );
      const panel = page.getByRole('tabpanel', {
        name: 'Plan information',
        exact: true,
      });
      await expect(panel).toBeVisible();
      const tab = page.getByRole('tab', {
        name: 'Plan information',
        exact: true,
      });
      await expect(tab).toHaveAttribute(
        'aria-controls',
        await panel.getAttribute('id'),
      );
      await expect(page.getByTestId('invoice-settings-button')).toBeEnabled();
      await scan(page, '[data-testid="plan-information"]');
      await page.screenshot({
        path: test.info().outputPath('03-plan-information.png'),
        fullPage: true,
      });
      const trigger = page.getByRole('button', {
        name: 'Invoice settings',
        exact: true,
      });
      await trigger.click();
      const dialog = page.getByRole('dialog', {name: 'Invoice settings'});
      await expect(dialog).toBeVisible();
      await page
        .getByRole('checkbox', {name: 'Send receipts with email'})
        .check();
      const email = page.getByRole('textbox', {name: 'Receipt email address'});
      await email.fill('bad');
      await expect(email).toHaveAccessibleDescription(
        /Enter a valid email address\./,
      );
      await expect(email).toHaveAttribute('aria-invalid', 'true');
      await expect(
        dialog.getByRole('button', {name: 'Save', exact: true}),
      ).toBeDisabled();
      await scan(page, '[role="dialog"]');
      await page.screenshot({
        path: test.info().outputPath('04-invoice-validation.png'),
      });
      await email.fill('receipts@example.com');
      await expect(email).not.toHaveAttribute('aria-invalid', 'true');
      for (const key of ['Tab', 'Shift+Tab']) {
        for (let step = 0; step < 12; step++) {
          await page.keyboard.press(key);
          await expect
            .poll(() =>
              dialog.evaluate((element) =>
                element.contains(document.activeElement),
              ),
            )
            .toBe(true);
        }
      }
      await page.keyboard.press('Escape');
      await expect(dialog).toHaveCount(0);
      await expect(trigger).toBeFocused();
      await trigger.click();
      await page
        .getByRole('checkbox', {name: 'Send receipts with email'})
        .check();
      await page
        .getByRole('textbox', {name: 'Receipt email address'})
        .fill('receipts@example.com');
      await page.getByRole('button', {name: 'Save', exact: true}).click();
      await expect(dialog).toHaveCount(0);
      await page.reload();
      await page
        .getByRole('button', {name: 'Invoice settings', exact: true})
        .click();
      await expect(
        page.getByRole('checkbox', {name: 'Send receipts with email'}),
      ).toBeChecked();
      await expect(
        page.getByRole('textbox', {name: 'Receipt email address'}),
      ).toHaveValue('receipts@example.com');
      await page.keyboard.press('Escape');
      await page
        .getByRole('link', {name: 'View invoices', exact: true})
        .click();
      await expect(
        page.getByRole('heading', {name: 'Invoices', exact: true}),
      ).toBeVisible();
      await scan(page, 'main');
      const downloads = page.getByRole('link', {
        name: /^Download PDF for invoice /,
      });
      if (await downloads.count())
        await expect(downloads.first()).toHaveAccessibleName(
          /^Download PDF for invoice /,
        );
      await page.screenshot({
        path: test.info().outputPath('05-invoices.png'),
        fullPage: true,
      });
    });

    test('scans simulated checkout and supports keyboard confirmation of an existing subscription change', async ({
      billingPage: page,
      billingAccount,
      api,
    }) => {
      test.skip(
        process.env.PLAYWRIGHT_FAKE_CHECKOUT !== 'true',
        'Requires the local FakeStripe provider.',
      );
      const {name} = await api.organization('accesspay');
      const {plans}: {plans: Plan[]} = await (
        await page.request.get('/api/v1/plans/')
      ).json();
      const paid = plans.filter(
        (plan) =>
          plan.bus_features &&
          plan.price > 0 &&
          !plan.deprecated &&
          !plan.plans_page_hidden,
      );
      expect(paid.length).toBeGreaterThan(1);
      await page.goto(`/organization/${name}/plans`);
      await page
        .getByRole('button', {name: `Select ${paid[0].title}`, exact: true})
        .click();
      await expect(page.getByTestId('fake-checkout-page')).toBeVisible();
      await scan(page, '[data-testid="fake-checkout-page"]');
      await page.screenshot({
        path: test.info().outputPath('06-simulated-checkout.png'),
        fullPage: true,
      });
      await page
        .getByRole('button', {name: 'Complete simulated checkout'})
        .click();
      const result = page.getByTestId('plan-change-result');
      await expect(result).toContainText('Your subscription has been updated.');
      await expect(result).toHaveAttribute('aria-live', 'polite');
      await page.screenshot({
        path: test.info().outputPath('07-confirmed-plan.png'),
        fullPage: true,
      });
      await page.goto(`/organization/${name}/plans`);
      const select = page.getByRole('button', {
        name: `Select ${paid[1].title}`,
        exact: true,
      });
      await select.focus();
      await page.keyboard.press('Enter');
      const dialog = page.getByRole('dialog', {name: 'Confirm plan change'});
      await expect(dialog).toBeVisible();
      await expect
        .poll(() =>
          dialog.evaluate((element) =>
            element.contains(document.activeElement),
          ),
        )
        .toBe(true);
      await page.keyboard.press('Tab');
      await expect
        .poll(() =>
          dialog.evaluate((element) =>
            element.contains(document.activeElement),
          ),
        )
        .toBe(true);
      await scan(page, '[role="dialog"]');
      await page.screenshot({
        path: test.info().outputPath('08-plan-change-dialog.png'),
      });
      await page.keyboard.press('Escape');
      await expect(dialog).toHaveCount(0);
      await expect(select).toBeFocused();
      await select.click();
      await page
        .getByRole('button', {name: 'Confirm change', exact: true})
        .click();
      await expect(page.getByTestId('plan-change-result')).toContainText(
        'Your subscription has been updated.',
      );
      const subscription = await (
        await billingAccount.context.request.get(
          `/api/v1/organization/${name}/plan`,
        )
      ).json();
      expect(subscription.plan).toBe(paid[1].stripeId);
    });
  },
);
