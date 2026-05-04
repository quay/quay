/**
 * Manifest Track Visualization Tests (PROJQUAY-9592)
 *
 * Tests the visual grouping indicators for tags that share the same manifest
 * digest in the tags table. Tags sharing a manifest are connected by colored
 * dots and vertical lines.
 *
 * Uses API mocking to simulate tag responses with controlled manifest digests.
 */

import {test, expect, CreatedRepo} from '../../fixtures';
import {Page} from '@playwright/test';

// Digest constants for deterministic test data
const DIGEST_A =
  'sha256:aaaa111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';
const DIGEST_B =
  'sha256:bbbb111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';
const DIGEST_C =
  'sha256:cccc111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';

function createMockTag(name: string, digest: string) {
  return {
    name,
    manifest_digest: digest,
    is_manifest_list: false,
    size: 1024,
    last_modified: new Date().toISOString(),
    reversion: false,
    start_ts: Math.floor(Date.now() / 1000),
  };
}

function createMockTagsResponse(tags: ReturnType<typeof createMockTag>[]) {
  return {
    tags,
    page: 1,
    has_additional: false,
  };
}

async function mockTagApi(
  page: Page,
  repo: CreatedRepo,
  tags: ReturnType<typeof createMockTag>[],
) {
  await page.route(
    `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createMockTagsResponse(tags)),
      });
    },
  );
}

test.describe('Manifest Track Visualization', {tag: ['@tags']}, () => {
  test('shows track column when tags share a manifest digest', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_C),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a'}),
    ).toBeVisible();

    const trackHeader = authenticatedPage.locator(
      'th[aria-label="Manifest tracks"]',
    );
    await expect(trackHeader).toBeVisible();
  });

  test('hides track column when all tags have unique digests', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_B),
      createMockTag('tag-c', DIGEST_C),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a'}),
    ).toBeVisible();

    const trackHeader = authenticatedPage.locator(
      'th[aria-label="Manifest tracks"]',
    );
    await expect(trackHeader).not.toBeAttached();
  });

  test('renders dot buttons only for tags sharing a manifest', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_C),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a'}),
    ).toBeVisible();

    // 2 dot buttons for the shared group (one per tag row)
    const dots = authenticatedPage.getByRole('button', {
      name: /Select all 2 tags with manifest/,
    });
    await expect(dots).toHaveCount(2);

    // The unique tag row should not have a dot button
    const uniqueRow = authenticatedPage.getByTestId('table-entry').filter({
      has: authenticatedPage.getByRole('link', {name: 'tag-c'}),
    });
    await expect(
      uniqueRow.getByRole('button', {name: /Select all/}),
    ).toHaveCount(0);
  });

  test('clicking dot selects all tags with the same manifest', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a1', DIGEST_A),
      createMockTag('tag-a2', DIGEST_A),
      createMockTag('tag-a3', DIGEST_A),
      createMockTag('tag-b1', DIGEST_B),
      createMockTag('tag-b2', DIGEST_B),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a1'}),
    ).toBeVisible();

    // Click the first dot for group A (3 tags sharing DIGEST_A)
    const dotA = authenticatedPage
      .getByRole('button', {
        name: /Select all 3 tags with manifest/,
      })
      .first();
    await dotA.click();

    // All group A tags should be checked
    for (const tagName of ['tag-a1', 'tag-a2', 'tag-a3']) {
      const row = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: tagName}),
      });
      await expect(row.getByRole('checkbox')).toBeChecked();
    }

    // Group B tags should not be checked
    for (const tagName of ['tag-b1', 'tag-b2']) {
      const row = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: tagName}),
      });
      await expect(row.getByRole('checkbox')).not.toBeChecked();
    }

    // Bulk Actions button should appear in toolbar
    await expect(
      authenticatedPage.getByTestId('bulk-actions-kebab'),
    ).toBeVisible();
  });

  test('dot aria-label conveys tag count and digest prefix', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_A),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a'}),
    ).toBeVisible();

    // Each dot's aria-label encodes the tag count and digest prefix,
    // providing the same information the tooltip displays.
    const expectedLabel = `Select all 3 tags with manifest ${DIGEST_A.substring(
      0,
      12,
    )}`;
    const dots = authenticatedPage.getByRole('button', {
      name: expectedLabel,
    });
    await expect(dots).toHaveCount(3);

    // Verify the full aria-label value on the first dot
    await expect(dots.first()).toHaveAttribute('aria-label', expectedLabel);
  });

  test('renders correct dots for multiple track groups', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a1', DIGEST_A),
      createMockTag('tag-a2', DIGEST_A),
      createMockTag('tag-a3', DIGEST_A),
      createMockTag('tag-b1', DIGEST_B),
      createMockTag('tag-b2', DIGEST_B),
      createMockTag('tag-b3', DIGEST_B),
      createMockTag('tag-u', DIGEST_C),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a1'}),
    ).toBeVisible();

    // Group A: 3 dots (one per tag sharing DIGEST_A)
    const dotsA = authenticatedPage.getByRole('button', {
      name: /Select all 3 tags with manifest sha256:aaaa1/,
    });
    await expect(dotsA).toHaveCount(3);

    // Group B: 3 dots (one per tag sharing DIGEST_B)
    const dotsB = authenticatedPage.getByRole('button', {
      name: /Select all 3 tags with manifest sha256:bbbb1/,
    });
    await expect(dotsB).toHaveCount(3);

    // Unique tag row has no dot
    const uniqueRow = authenticatedPage.getByTestId('table-entry').filter({
      has: authenticatedPage.getByRole('link', {name: 'tag-u'}),
    });
    await expect(
      uniqueRow.getByRole('button', {name: /Select all/}),
    ).toHaveCount(0);
  });

  test('unique tag row has no manifest track dot', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_C),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-c'}),
    ).toBeVisible();

    const uniqueRow = authenticatedPage.getByTestId('table-entry').filter({
      has: authenticatedPage.getByRole('link', {name: 'tag-c'}),
    });
    await expect(uniqueRow.locator('.manifest-track-dot')).toHaveCount(0);
  });

  test('supports keyboard activation of track dots', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    await mockTagApi(authenticatedPage, repo, [
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
    ]);

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'tag-a'}),
    ).toBeVisible();

    // Verify accessibility attributes on the dot
    const dot = authenticatedPage
      .getByRole('button', {
        name: /Select all 2 tags with manifest/,
      })
      .first();
    await expect(dot).toHaveAttribute('role', 'button');
    await expect(dot).toHaveAttribute('tabindex', '0');

    // Activate via keyboard (focus + Enter)
    await dot.focus();
    await authenticatedPage.keyboard.press('Enter');

    // Both tags should be selected
    for (const tagName of ['tag-a', 'tag-b']) {
      const row = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: tagName}),
      });
      await expect(row.getByRole('checkbox')).toBeChecked();
    }
  });
});
