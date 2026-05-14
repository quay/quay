import {test, expect} from '../../fixtures';
import {execSync} from 'node:child_process';

const SUPERVISORCTL =
  'podman exec quay-quay supervisorctl -s unix:///tmp/supervisord.sock';

function stopWebBackend() {
  execSync(`${SUPERVISORCTL} stop gunicorn-web`, {timeout: 10000});
}

function startWebBackend() {
  execSync(`${SUPERVISORCTL} start gunicorn-web`, {timeout: 10000});
}

test.describe.serial(
  'Nginx 502 error page when backend is unreachable',
  {tag: ['@ui']},
  () => {
    test.afterAll(() => {
      try {
        startWebBackend();
      } catch {
        // best-effort restart
      }
    });

    test('returns 502 status with loading page when backend is down', async ({
      browser,
    }) => {
      stopWebBackend();

      const context = await browser.newContext();
      const page = await context.newPage();
      try {
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

    test('API endpoints also return 502 when backend is down', async ({
      playwright,
    }) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.get(
          'http://localhost:8080/api/v1/discovery',
        );
        expect(response.status()).toBe(502);
      } finally {
        await request.dispose();
      }
    });

    test('backend recovers and serves 200 after restart', async ({browser}) => {
      startWebBackend();

      // Wait for gunicorn to be ready
      const context = await browser.newContext();
      const page = await context.newPage();
      try {
        await page.waitForTimeout(2000);
        const response = await page.goto('/', {timeout: 30000});
        expect(response?.status()).toBe(200);
      } finally {
        await page.close();
        await context.close();
      }
    });
  },
);
