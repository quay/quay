import {expect, type Locator, type Page} from '@playwright/test';

export function nsNotificationsTable(page: Page): Locator {
  return page.getByTestId('ns-notifications-table');
}

export function nsNotificationRow(page: Page, title: string | RegExp): Locator {
  const table = nsNotificationsTable(page);
  // Inner locator is resolved relative to each candidate row (not the table).
  return table.getByRole('row').filter({
    has: page.locator('[data-label="title"]', {hasText: title}),
  });
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
      row.locator('[data-label="event"]', {hasText: columns.event}),
    ).toBeVisible();
  }
  if (columns.method) {
    await expect(
      row.locator('[data-label="method"]', {hasText: columns.method}),
    ).toBeVisible();
  }
  if (columns.status) {
    await expect(
      row.locator('[data-label="status"]', {hasText: columns.status}),
    ).toBeVisible();
  }
}

export async function closeNotificationModal(page: Page): Promise<void> {
  const modal = page.getByRole('dialog');
  await modal.getByLabel('Close', {exact: true}).click();
}

export async function selectTeamRecipient(
  page: Page,
  teamName: string,
): Promise<void> {
  await page.locator('#entity-search-input').click();
  await page.getByTestId(`${teamName}-team`).click();
}
