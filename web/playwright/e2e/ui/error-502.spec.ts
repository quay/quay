import {test, expect} from '../../fixtures';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const ERROR_PAGE_PATH = resolve(__dirname, '../../../../static/502.html');

test.describe(
  'Nginx 502 error page when backend is unreachable',
  {tag: ['@ui']},
  () => {
    test('renders the 502 loading page with correct content', async ({
      browser,
    }): Promise<void> => {
      const errorPageHtml = readFileSync(ERROR_PAGE_PATH, 'utf-8');

      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await page.route('**/*', async (route): Promise<void> => {
          await route.fulfill({
            status: 502,
            contentType: 'text/html',
            body: errorPageHtml,
          });
        });

        const response = await page.goto('/');

        expect(response?.status()).toBe(502);
        await expect(page).toHaveTitle('Quay Loading');
        await expect(page.getByText('Quay is currently loading')).toBeVisible();
        await expect(
          page.getByText(
            'Please wait and refresh the page shortly to try again.',
          ),
        ).toBeVisible();
      } finally {
        await page.close();
        await context.close();
      }
    });
  },
);
