import {expect, type Locator, type Page} from '@playwright/test';

export function nsNotificationsTable(page: Page): Locator {
  return page.getByTestId('ns-notifications-table');
}

export function nsNotificationRow(page: Page, title: string | RegExp): Locator {
  return nsNotificationsTable(page).getByRole('row', {name: title});
}

export async function expectNsNotificationRow(
  page: Page,
  title: string | RegExp,
  columns: {event?: string; method?: string; status?: string} = {},
): Promise<void> {
  const row = nsNotificationRow(page, title);
  await expect(row).toBeVisible();
  if (columns.event) {
    await expect(
      row.getByRole('gridcell', {name: columns.event, exact: true}),
    ).toBeVisible();
  }
  if (columns.method) {
    await expect(
      row.getByRole('gridcell', {name: columns.method, exact: true}),
    ).toBeVisible();
  }
  if (columns.status) {
    await expect(
      row.getByRole('gridcell', {name: columns.status, exact: true}),
    ).toBeVisible();
  }
}

export async function closeNotificationModal(page: Page): Promise<void> {
  const modal = page.getByRole('dialog');
  await modal.getByRole('button', {name: 'Close'}).click();
}

export async function selectTeamRecipient(
  page: Page,
  teamName: string,
): Promise<void> {
  await page.locator('#entity-search-input').click();
  await page.getByTestId(`${teamName}-team`).click();
}
