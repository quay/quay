import {test, expect, WebhookReceiver} from '../../fixtures';

test.describe(
  'Webhook Delivery Verification',
  {tag: ['@repository', '@PROJQUAY-11627']},
  () => {
    let webhook: WebhookReceiver;

    test.beforeEach(async () => {
      webhook = new WebhookReceiver();
      await webhook.start();
    });

    test.afterEach(async () => {
      await webhook.stop();
    });

    test(
      'delivers webhook payload on repo_push test fire',
      {tag: '@webhook'},
      async ({api}) => {
        const org = await api.organization('whdlv');
        const repo = await api.repository(org.name, 'pushwebhook');

        const notification = await api.notification(
          org.name,
          repo.name,
          'repo_push',
          'webhook',
          {url: webhook.getUrl()},
          'Push Webhook Test',
        );

        await api.raw.testRepositoryNotification(
          org.name,
          repo.name,
          notification.uuid,
        );

        const received = await webhook.waitForWebhook();
        expect(received).not.toBeNull();

        const body = received!.body;
        expect(body).toHaveProperty('repository');
        expect(body).toHaveProperty('namespace');
        expect(body).toHaveProperty('name');
        expect(body).toHaveProperty('docker_url');
        expect(body).toHaveProperty('homepage');
        expect(body).toHaveProperty('updated_tags');
        expect(body['updated_tags']).toEqual(
          expect.arrayContaining(['latest', 'foo']),
        );

        expect(received!.headers['content-type']).toBe('application/json');
      },
    );

    test(
      'delivers webhook payload on vulnerability_found test fire',
      {tag: '@webhook'},
      async ({api}) => {
        const org = await api.organization('whdlv');
        const repo = await api.repository(org.name, 'vulnwebhook');

        const notification = await api.notification(
          org.name,
          repo.name,
          'vulnerability_found',
          'webhook',
          {url: webhook.getUrl()},
          'Vulnerability Webhook Test',
        );

        await api.raw.testRepositoryNotification(
          org.name,
          repo.name,
          notification.uuid,
        );

        const received = await webhook.waitForWebhook();
        expect(received).not.toBeNull();

        const body = received!.body;
        expect(body).toHaveProperty('repository');
        expect(body).toHaveProperty('namespace');
        expect(body).toHaveProperty('name');
        expect(body).toHaveProperty('docker_url');
        expect(body).toHaveProperty('homepage');
        expect(body).toHaveProperty('tags');
        expect(body).toHaveProperty('vulnerability');

        const vuln = body['vulnerability'] as Record<string, unknown>;
        expect(vuln).toHaveProperty('id');
        expect(vuln).toHaveProperty('description');
        expect(vuln).toHaveProperty('link');
        expect(vuln).toHaveProperty('priority');
      },
    );

    test(
      'delivers webhook payload on repo_image_expiry test fire',
      {tag: ['@feature:IMAGE_EXPIRY_TRIGGER', '@webhook']},
      async ({api}) => {
        const org = await api.organization('whdlv');
        const repo = await api.repository(org.name, 'expirywebhook');

        const notification = await api.notification(
          org.name,
          repo.name,
          'repo_image_expiry',
          'webhook',
          {url: webhook.getUrl()},
          'Expiry Webhook Test',
        );

        await api.raw.testRepositoryNotification(
          org.name,
          repo.name,
          notification.uuid,
        );

        const received = await webhook.waitForWebhook();
        expect(received).not.toBeNull();

        const body = received!.body;
        expect(body).toHaveProperty('repository');
        expect(body).toHaveProperty('namespace');
        expect(body).toHaveProperty('name');
        expect(body).toHaveProperty('docker_url');
        expect(body).toHaveProperty('homepage');
        expect(body).toHaveProperty('tags');
        expect(body).toHaveProperty('expiring_in');
      },
    );
  },
);
