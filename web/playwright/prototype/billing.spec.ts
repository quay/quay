import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';

const planInfo =
  '/organization/user1?tab=Settings&settingsTab=billinginformation';

test('the complete Stripe catalog matches the plan names, prices, and limits in the reference', async ({
  page,
}) => {
  await page.goto('/organization/user1/plans');
  const current = page.getByTestId('current-plan-card');
  await expect(
    current.getByRole('heading', {name: 'Medium', exact: true}),
  ).toBeVisible();
  await expect(current).toContainText('$125/month');
  await expect(current).toContainText('12 used of 50');

  const available = [
    ['free', 'Open Source', 0, 0],
    ['personal-2018', 'Developer', 15, 5],
    ['bus-micro-2018', 'Micro', 30, 10],
    ['bus-small-2018', 'Small', 60, 20],
    ['bus-large-2018', 'Large', 250, 125],
    ['bus-xlarge-2018', 'Extra Large', 450, 250],
    ['bus-500-2018', 'XXL', 850, 500],
    ['bus-1000-2018', 'XXXL', 1600, 1000],
    ['bus-2000-2018', 'XXXXL', 3100, 2000],
    ['price_1LRztA2OoNF1TIf0SvSrz106', 'XXXXXL', 21700, 15000],
  ] as const;
  await expect(page.getByTestId(/^available-plan-/)).toHaveCount(10);
  for (const [id, title, price, repositories] of available) {
    const card = page.getByTestId(`available-plan-${id}`);
    await expect(
      card.getByRole('heading', {name: title, exact: true}),
    ).toBeVisible();
    await expect(card).toContainText(
      price === 0 ? 'Free' : `$${price.toFixed(2)}/month`,
    );
    await expect(card).toContainText(
      repositories === 0
        ? 'No private repositories'
        : `${repositories} private repositories`,
    );
  }
  await page.screenshot({
    path: '/private/tmp/quay-complete-plan-catalog.png',
    fullPage: true,
  });

  // Each paid tier opens its own correctly priced checkout and cancels safely.
  for (const [, title, price] of available.filter((entry) => entry[2] > 0)) {
    await page
      .getByRole('button', {name: `Select ${title}`, exact: true})
      .click();
    await expect(
      page.getByRole('heading', {name: `Subscribe to ${title}`, exact: true}),
    ).toBeVisible();
    await expect(
      page.getByText(`$${price.toFixed(2)}`, {exact: true}),
    ).toBeVisible();
    await page.getByRole('link', {name: 'Cancel', exact: true}).click();
    await expect(
      page.getByRole('heading', {name: 'Medium', exact: true}),
    ).toBeVisible();
    await page.getByRole('button', {name: 'Change Plan', exact: true}).click();
  }
  await page
    .getByRole('button', {name: 'Select Open Source', exact: true})
    .click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Open Source');
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(
    current.getByRole('heading', {name: 'Medium', exact: true}),
  ).toBeVisible();
});

test('every invoice downloads a PDF and the breadcrumb returns to Plan information', async ({
  page,
}) => {
  await page.goto('/organization/user1/invoices');
  await expect(
    page.getByRole('heading', {name: 'Invoices', exact: true}),
  ).toBeVisible();
  await expect(
    page.getByRole('gridcell', {name: '9/12/2026', exact: true}),
  ).toBeVisible();
  for (const id of ['inv_1', 'inv_2', 'inv_3']) {
    const downloaded = page.waitForEvent('download');
    await page
      .getByRole('link', {name: `Download invoice ${id} as PDF`})
      .click();
    const download = await downloaded;
    expect(download.suggestedFilename()).toBe(`quay-invoice-${id}.pdf`);
    const path = await download.path();
    expect((await readFile(path)).subarray(0, 5).toString()).toBe('%PDF-');
  }
  await page.screenshot({
    path: '/private/tmp/quay-billing-invoices.png',
    fullPage: true,
  });
  await page.getByRole('link', {name: 'Plan information', exact: true}).click();
  await expect(page).toHaveURL(/settingsTab=billinginformation/);
  await expect(
    page.getByRole('button', {name: 'Change Plan', exact: true}),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole('tab', {name: 'Plan information'}),
  ).toHaveAttribute('aria-selected', 'true');
});

test('invoice keyword search filters and clears while bulk download includes the complete history', async ({
  page,
}) => {
  await page.goto('/organization/user1/invoices');
  const search = page.getByLabel('Search invoices', {exact: true});
  const invoiceDownloads = page.getByRole('link', {
    name: /Download invoice .* as PDF/,
  });
  await expect(invoiceDownloads).toHaveCount(3);
  await search.fill('INV_2');
  await expect(invoiceDownloads).toHaveCount(1);
  await expect(
    page.getByRole('link', {name: 'Download invoice inv_2 as PDF'}),
  ).toBeVisible();
  await search.fill('Paid');
  await expect(invoiceDownloads).toHaveCount(2);
  await search.fill('unpaid');
  await expect(invoiceDownloads).toHaveCount(1);
  await expect(page.getByTestId('invoice-results-summary')).toHaveText(
    '1 of 3 invoices',
  );

  const downloaded = page.waitForEvent('download');
  await page
    .getByRole('link', {name: 'Download all invoices', exact: true})
    .click();
  const download = await downloaded;
  expect(download.suggestedFilename()).toBe('quay-user1-invoices.zip');
  const zipPath = await download.path();
  const entries = JSON.parse(
    execFileSync(
      'python3',
      [
        '-c',
        'import json, sys, zipfile; archive = zipfile.ZipFile(sys.argv[1]); assert archive.testzip() is None; print(json.dumps([{ "name": name, "pdf": archive.read(name).startswith(b"%PDF-") } for name in archive.namelist()]))',
        zipPath,
      ],
      {encoding: 'utf8'},
    ),
  ) as {name: string; pdf: boolean}[];
  expect(entries.map((entry) => entry.name).sort()).toEqual([
    'quay-invoice-inv_1.pdf',
    'quay-invoice-inv_2.pdf',
    'quay-invoice-inv_3.pdf',
  ]);
  expect(entries.every((entry) => entry.pdf)).toBe(true);

  await search.fill('September 2026');
  await expect(invoiceDownloads).toHaveCount(1);
  await search.fill('$125.00 medium');
  await expect(invoiceDownloads).toHaveCount(3);
  await search.fill('not-found');
  await expect(
    page.getByRole('heading', {name: 'No matching invoices', exact: true}),
  ).toBeVisible();
  await expect(invoiceDownloads).toHaveCount(0);
  await page
    .getByRole('button', {name: 'Clear invoice search', exact: true})
    .click();
  await expect(search).toHaveValue('');
  await expect(invoiceDownloads).toHaveCount(3);
  await page.screenshot({
    path: '/private/tmp/quay-invoice-search-and-bulk-download.png',
  });
  await page.setViewportSize({width: 390, height: 844});
  if (
    await page
      .getByRole('navigation', {name: 'Global', exact: true})
      .isVisible()
  ) {
    await page
      .getByRole('button', {name: 'Global navigation', exact: true})
      .click();
  }
  await expect(search).toBeVisible();
  await expect(
    page.getByRole('link', {name: 'Download all invoices', exact: true}),
  ).toBeVisible();
  const width = await page.getByRole('main').evaluate((element) => ({
    content: element.scrollWidth,
    viewport: element.clientWidth,
  }));
  expect(width.content).toBeLessThanOrEqual(width.viewport);
  await page.screenshot({path: '/private/tmp/quay-invoice-search-mobile.png'});
});

test('available plans open Stripe checkout; cancel preserves the plan and subscribe persists the selection', async ({
  page,
}) => {
  await page.goto('/organization/user1/plans');
  const current = page.getByTestId('current-plan-card');
  await expect(
    current.getByRole('heading', {name: 'Medium', exact: true}),
  ).toBeVisible();
  await expect(page.getByTestId('available-plan-bus-medium-2018')).toHaveCount(
    0,
  );
  await page.screenshot({
    path: '/private/tmp/quay-billing-plans.png',
    fullPage: true,
  });
  await page.getByRole('button', {name: 'Select Large'}).click();
  await expect(
    page.getByRole('heading', {name: 'Subscribe to Large'}),
  ).toBeVisible();
  await expect(page.getByText('$250.00', {exact: true})).toBeVisible();
  await page.getByRole('link', {name: 'Cancel', exact: true}).click();
  await expect(
    page.getByRole('heading', {name: 'Medium', exact: true}),
  ).toBeVisible();
  await page.getByRole('button', {name: 'Change Plan', exact: true}).click();
  await page.getByRole('button', {name: 'Select Large'}).click();
  await page.getByLabel('Cardholder name').fill('Sample Cardholder');
  await page.getByLabel('Card number').fill('4242 4242 4242 4242');
  await page.getByLabel('Expiration date').fill('12/30');
  await page.getByLabel('Security code').fill('123');
  await page.getByLabel('ZIP', {exact: true}).fill('10001');
  await page.getByRole('button', {name: 'Subscribe', exact: true}).click();
  await expect(page).toHaveURL(/settingsTab=billinginformation/);
  await expect(
    page.getByRole('heading', {name: 'Large', exact: true}),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole('heading', {name: 'Large', exact: true}),
  ).toBeVisible();
  await page.goto('/organization/projectquay/plans');
  await expect(
    current.getByRole('heading', {name: 'Medium', exact: true}),
  ).toBeVisible();
  await page.getByRole('link', {name: 'Plan information', exact: true}).click();
  await expect(page).toHaveURL(
    /organization\/projectquay\?.*settingsTab=billinginformation/,
  );
});

test('Plan information summaries link to subscriptions and invoices without inline settings', async ({
  page,
}) => {
  await page.goto(planInfo);
  await expect(page.getByTestId('subscription-summary')).toHaveText(
    '2 subscriptions',
  );
  await expect(page.getByTestId('invoice-summary')).toHaveText('3 invoices');
  await expect(
    page.getByRole('button', {name: 'Select saved card'}),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', {name: 'Save', exact: true}),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', {name: 'Cancel', exact: true}),
  ).toHaveCount(0);
  await expect(page.getByLabel('Receipt email address')).toHaveCount(0);
  await page.screenshot({
    path: '/private/tmp/quay-plan-information-updated.png',
  });
  await page
    .getByRole('link', {name: 'View subscriptions', exact: true})
    .click();
  await expect(page).toHaveURL(/organization\/user1\/subscriptions$/);
  await expect(page.getByTestId(/^subscription-row-/)).toHaveCount(2);
  await expect(page.getByTestId('subscription-row-sub_user_1')).toContainText(
    'projectquay',
  );
  await expect(page.getByTestId('subscription-row-sub_user_2')).toContainText(
    'user1',
  );
  await page.screenshot({
    path: '/private/tmp/quay-customer-portal-subscriptions.png',
  });
  await page.getByRole('link', {name: 'Plan information', exact: true}).click();
  await expect(page.getByTestId('subscription-summary')).toHaveText(
    '2 subscriptions',
  );
  await page.getByRole('link', {name: 'View invoices', exact: true}).click();
  await expect(page).toHaveURL(/organization\/user1\/invoices$/);
  await expect(
    page.getByRole('link', {name: /Download invoice .* as PDF/}),
  ).toHaveCount(3);
});

test('invoice settings save, cancel, validate, refresh, and stay separate for each namespace', async ({
  page,
}) => {
  await page.goto(planInfo);
  const trigger = page.getByRole('button', {
    name: 'Invoice settings',
    exact: true,
  });
  const dialog = page.getByRole('dialog', {
    name: 'Invoice settings',
    exact: true,
  });
  const checkbox = dialog.getByRole('checkbox', {
    name: 'Send receipts with email',
  });
  const email = dialog.getByLabel('Receipt email address');
  await trigger.click();
  await expect(checkbox).toBeChecked();
  await expect(email).toHaveValue('user1@redhat.com');
  await page.screenshot({path: '/private/tmp/quay-invoice-settings-modal.png'});
  await email.fill('discard@example.com');
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect(email).toHaveValue('user1@redhat.com');
  await checkbox.uncheck();
  await page.keyboard.press('Escape');
  await trigger.click();
  await expect(checkbox).toBeChecked();
  await email.fill('invalid');
  await expect(
    dialog.getByRole('button', {name: 'Save', exact: true}),
  ).toBeDisabled();
  await expect(dialog.getByText('Enter a valid email address.')).toBeVisible();
  await email.fill('receipts@example.com');
  await email.press('Enter');
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await trigger.click();
  await expect(email).toHaveValue('receipts@example.com');
  await checkbox.uncheck();
  await expect(email).toBeDisabled();
  await dialog.getByRole('button', {name: 'Save', exact: true}).click();
  await expect(dialog).toHaveCount(0);
  await page.goto(
    '/organization/projectquay?tab=Settings&settingsTab=billinginformation',
  );
  await trigger.click();
  await expect(checkbox).toBeChecked();
  await expect(email).toHaveValue('quay-devel+projectquay@redhat.com');
  await email.fill('organization-receipts@example.com');
  await dialog.getByRole('button', {name: 'Save', exact: true}).click();
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await trigger.click();
  await expect(email).toHaveValue('organization-receipts@example.com');
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  await page.goto(planInfo);
  await trigger.click();
  await expect(checkbox).not.toBeChecked();
  await expect(email).toHaveValue('receipts@example.com');
});

test('receipt save failures keep the modal open and preserve the saved preferences', async ({
  page,
}) => {
  await page.goto(planInfo);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith('quay-receipt-settings-prototype-v1:'))
        throw new Error('Storage unavailable');
      return original.call(this, key, value);
    };
  });
  await page
    .getByRole('button', {name: 'Invoice settings', exact: true})
    .click();
  const dialog = page.getByRole('dialog', {
    name: 'Invoice settings',
    exact: true,
  });
  await dialog.getByLabel('Receipt email address').fill('unsaved@example.com');
  await dialog.getByRole('button', {name: 'Save', exact: true}).click();
  await expect(
    dialog.getByText('Unable to save invoice settings'),
  ).toBeVisible();
  await expect(dialog.getByLabel('Receipt email address')).toHaveValue(
    'unsaved@example.com',
  );
  await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
  await page.reload();
  await page
    .getByRole('button', {name: 'Invoice settings', exact: true})
    .click();
  await expect(page.getByLabel('Receipt email address')).toHaveValue(
    'user1@redhat.com',
  );
});

test('organization subscription attachment and removal update the list, summary, and assignment', async ({
  page,
}) => {
  await page.goto('/organization/testorg/subscriptions');
  await expect(
    page.getByRole('heading', {name: 'No subscriptions', exact: true}),
  ).toBeVisible();
  await page
    .getByRole('button', {name: 'Attach subscriptions', exact: true})
    .click();
  let dialog = page.getByRole('dialog', {
    name: 'Attach subscription',
    exact: true,
  });
  await expect(
    dialog.getByRole('button', {name: 'Confirm', exact: true}),
  ).toBeDisabled();
  await dialog.getByTestId('subscription-select-toggle').click();
  await page
    .getByRole('option', {name: '1x MW01885 (sub_user_2)', exact: true})
    .press('Enter');
  await dialog.getByRole('button', {name: 'Confirm', exact: true}).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByTestId('subscription-row-sub_user_2')).toContainText(
    'testorg',
  );
  await page.reload();
  await expect(page.getByTestId(/^subscription-row-/)).toHaveCount(1);
  await page.getByRole('link', {name: 'Plan information', exact: true}).click();
  await expect(page.getByTestId('subscription-summary')).toHaveText(
    '1 subscription',
  );
  await page
    .getByRole('link', {name: 'View subscriptions', exact: true})
    .click();
  await page
    .getByRole('button', {name: 'Remove subscriptions', exact: true})
    .click();
  dialog = page.getByRole('dialog', {name: 'Remove subscription', exact: true});
  await dialog.getByTestId('subscription-select-toggle').click();
  await page
    .getByRole('option', {name: '1x MW01885 (sub_user_2)', exact: true})
    .click();
  await dialog.getByRole('button', {name: 'Confirm', exact: true}).click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole('heading', {name: 'No subscriptions', exact: true}),
  ).toBeVisible();
  await page.getByRole('link', {name: 'Plan information', exact: true}).click();
  await expect(page.getByTestId('subscription-summary')).toHaveText(
    '0 subscriptions',
  );
  await page.goto('/organization/user1/subscriptions');
  await expect(page.getByTestId('subscription-row-sub_user_2')).toContainText(
    'user1',
  );
  await page.goto('/organization/projectquay/subscriptions');
  await expect(page.getByTestId(/^subscription-row-/)).toHaveCount(1);
  await expect(page.getByTestId('subscription-row-sub_user_1')).toContainText(
    'projectquay',
  );
});

test('adding a sample card in the full-page checkout validates and saves the masked card', async ({
  page,
}) => {
  await page.goto(planInfo);
  await page.getByRole('button', {name: 'Change payment method'}).click();
  await expect(page).toHaveURL(/prototypeCheckout=1/);
  await expect(page.getByTestId('stripe-checkout-page')).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page
    .getByRole('button', {name: 'Save payment method', exact: true})
    .click();
  await expect(page.getByText('Enter the cardholder name.')).toBeVisible();
  await page.getByLabel('Cardholder name').fill('Sample Cardholder');
  await page.getByLabel('Card number').fill('5555 5555 5555 4444');
  await page.getByLabel('Expiration date').fill('12/30');
  await page.getByLabel('Security code').fill('123');
  await page
    .getByRole('button', {name: 'Save payment method', exact: true})
    .click();
  await expect(page.getByText('Enter a valid ZIP code.')).toBeVisible();
  await page.getByLabel('ZIP', {exact: true}).fill('10001');
  await page
    .getByRole('button', {name: 'Save payment method', exact: true})
    .click();
  await expect(page).not.toHaveURL(/prototypeCheckout/);
  const stored = page.getByTestId('stored-payment-method');
  await expect(stored).toContainText('Mastercard');
  await expect(stored).toContainText('Sample Cardholder');
  await expect(stored).toContainText('4444');
  await page.reload();
  await expect(stored).toContainText('Sample Cardholder');
  await expect(
    page.getByRole('button', {name: 'Select saved card'}),
  ).toHaveCount(0);
});

test('canceling checkout returns to Plan information without changing the saved card', async ({
  page,
}) => {
  await page.goto(planInfo);
  await page.getByRole('button', {name: 'Change payment method'}).click();
  await expect(page).toHaveURL(/prototypeCheckout=1/);
  await expect(page.getByTestId('stripe-checkout-page')).toBeVisible();
  await page.getByRole('link', {name: 'Cancel', exact: true}).click();
  await expect(page).not.toHaveURL(/prototypeCheckout/);
  await expect(page.getByTestId('stored-payment-method')).toContainText('4242');
  await expect(
    page.getByRole('tab', {name: 'Plan information'}),
  ).toHaveAttribute('aria-selected', 'true');
});

test('the billing pages and payment dialog fit a mobile viewport', async ({
  page,
}) => {
  await page.setViewportSize({width: 390, height: 844});
  for (const url of [
    '/organization/user1/plans',
    '/organization/user1/invoices',
    '/organization/user1/subscriptions',
  ]) {
    await page.goto(url);
    await expect(
      page.getByRole('link', {name: 'Plan information', exact: true}),
    ).toBeVisible();
    // The shared masthead has its own mobile overflow. Check the billing
    // content within the page's main region independently of that header.
    const width = await page.getByRole('main').evaluate((element) => ({
      content: element.scrollWidth,
      viewport: element.clientWidth,
    }));
    expect(width.content).toBeLessThanOrEqual(width.viewport);
  }
  await page.goto(planInfo);
  await page
    .getByRole('button', {name: 'Invoice settings', exact: true})
    .click();
  await expect(
    page.getByRole('dialog', {name: 'Invoice settings', exact: true}),
  ).toBeVisible();
  await page.screenshot({
    path: '/private/tmp/quay-invoice-settings-mobile.png',
  });
  await page.getByRole('button', {name: 'Cancel', exact: true}).click();
  await page.getByRole('button', {name: 'Change payment method'}).click();
  await expect(page.getByLabel('Card number')).toBeVisible();
  const checkoutWidth = await page.evaluate(() => ({
    content: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(checkoutWidth.content).toBeLessThanOrEqual(checkoutWidth.viewport);
  await page.screenshot({
    path: '/private/tmp/quay-stripe-checkout-mobile.png',
    fullPage: true,
  });
});

test('checkout matches the full-page reference and its fields and wallet controls work', async ({
  page,
}) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  await page.setViewportSize({width: 1511, height: 861});
  await page.goto(planInfo + '&prototypeCheckout=1');
  await expect(
    page.getByRole('heading', {name: 'Contact information'}),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', {name: 'Payment method', exact: true}),
  ).toBeVisible();
  await expect(page.getByRole('navigation', {name: 'Global'})).toHaveCount(0);
  await expect(page.locator('#stripe-checkout')).toHaveCount(0);
  await page.screenshot({
    path: '/private/tmp/quay-stripe-checkout-desktop.png',
  });
  await page
    .getByRole('checkbox', {name: /Save my information with Link/})
    .uncheck();
  await expect(page.getByLabel('Phone number')).toHaveCount(0);
  await page.getByLabel('Country or region').selectOption('CA');
  await expect(page.getByLabel('Postal code', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Apple Pay', exact: true}).click();
  await expect(page.getByRole('dialog', {name: 'Apple Pay'})).toBeVisible();
  await page
    .getByRole('dialog')
    .getByRole('button', {name: 'Cancel', exact: true})
    .click();
  await page.getByRole('button', {name: 'Pay with Link'}).click();
  await expect(
    page.getByRole('dialog', {name: 'Link', exact: true}),
  ).toBeVisible();
  await page
    .getByRole('dialog')
    .getByRole('button', {name: 'Cancel', exact: true})
    .click();
  await page.getByRole('radio', {name: 'Google Pay', exact: true}).check();
  await expect(
    page.getByText('Visa ending in 4242', {exact: true}),
  ).toBeVisible();
  // Check the standalone checkout before returning to Quay's existing shell,
  // which has separate mock backend/static asset fallbacks.
  expect(consoleErrors).toEqual([]);
  await page.getByRole('link', {name: 'Back to Plan information'}).click();
  await expect(page.getByTestId('stored-payment-method')).toContainText('4242');
  expect(pageErrors).toEqual([]);
});

test('the selected fifteen dollar plan appears in the screenshot-style subscription checkout', async ({
  page,
}) => {
  await page.setViewportSize({width: 1511, height: 861});
  await page.goto('/organization/user1/plans');
  await page
    .getByRole('button', {name: 'Select Developer', exact: true})
    .click();
  await expect(
    page.getByRole('heading', {name: 'Subscribe to Developer'}),
  ).toBeVisible();
  await expect(page.getByText('$15.00', {exact: true})).toBeVisible();
  await expect(
    page.getByRole('button', {name: 'Subscribe', exact: true}),
  ).toBeVisible();
  // Restore the top of the scrollable checkout for a comparison at the same state.
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: '/private/tmp/quay-stripe-subscription-desktop.png',
  });
  await page.getByRole('link', {name: 'Back to Plan information'}).click();
  await expect(
    page.getByRole('heading', {name: 'Medium', exact: true}),
  ).toBeVisible();
});
