import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage, pushQuotaNotificationImage} from '../../utils/container';
import {WebhookReceiver} from '../../utils/webhook';
import {mailpit} from '../../utils/mailpit';

test.describe(
  'Namespace Notifications — Delivery',
  {tag: ['@organization', '@feature:QUOTA_NOTIFICATIONS']},
  () => {
    test(
      'webhook fires on quota warning threshold crossing',
      {
        tag: [
          '@feature:QUOTA_MANAGEMENT',
          '@feature:EDIT_QUOTA',
          '@container',
          '@superuser',
          '@webhook',
        ],
      },
      async ({api, superuserApi}) => {
        test.setTimeout(300_000);

        const org = await api.organization('nsdelivwarn');

        // Set up quota (3 MiB) with warning limit at 80% (~2.4 MiB threshold)
        const quota = await superuserApi.quota(org.name, 3145728);
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Warning',
          80,
        );

        // Start webhook receiver
        const receiver = new WebhookReceiver();
        await receiver.start();
        try {
          // Create webhook notification for quota_warning
          await api.namespaceNotification(
            org.name,
            'quota_warning',
            'webhook',
            {url: receiver.getUrl()},
            {},
            'Warning Webhook',
          );

          // Push pinned UBI image — one push exceeds threshold; second starts upload
          await api.repositoryWithName(org.name, 'repo1');
          await api.repositoryWithName(org.name, 'repo2');
          await pushQuotaNotificationImage(
            org.name,
            'repo1',
            'v1',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );
          await pushQuotaNotificationImage(
            org.name,
            'repo2',
            'v2',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );

          // Wait for webhook
          const webhook = await receiver.waitForWebhook(undefined, 60_000);
          expect(webhook).not.toBeNull();
          expect(webhook?.body).toHaveProperty('namespace');
          expect(webhook?.body).toHaveProperty('threshold_percent');

          // PROJQUAY-12230: verify numeric fields are serialized correctly
          // (Decimal from PostgreSQL SUM()/BigIntegerField must be cast to int before json.dumps)
          expect(typeof webhook?.body?.limit_bytes).toBe('number');
          expect(typeof webhook?.body?.usage_bytes).toBe('number');
          expect(typeof webhook?.body?.usage_percent).toBe('number');
          expect(typeof webhook?.body?.threshold_percent).toBe('number');
        } finally {
          await receiver.stop();
        }
      },
    );

    test(
      'webhook fires on quota error (reject) threshold crossing',
      {
        tag: [
          '@feature:QUOTA_MANAGEMENT',
          '@feature:EDIT_QUOTA',
          '@container',
          '@superuser',
          '@webhook',
        ],
      },
      async ({api, superuserApi}) => {
        test.setTimeout(120_000);

        const org = await api.organization('nsdeliverr');

        // Set up quota (2 MiB) with reject limit at 100%
        const quota = await superuserApi.quota(org.name, 2097152);
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Reject',
          100,
        );

        // Start webhook receiver
        const receiver = new WebhookReceiver();
        await receiver.start();
        try {
          // Create webhook notification for quota_error
          await api.namespaceNotification(
            org.name,
            'quota_error',
            'webhook',
            {url: receiver.getUrl()},
            {},
            'Error Webhook',
          );

          // busybox (~1.2 MiB): first push under 2 MiB quota, second rejected over limit
          await api.repositoryWithName(org.name, 'fillrepo');
          await pushImage(
            org.name,
            'fillrepo',
            'v1',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );

          // Second push should be rejected (over quota)
          try {
            await pushImage(
              org.name,
              'fillrepo',
              'v2',
              TEST_USERS.user.username,
              TEST_USERS.user.password,
            );
          } catch {
            // Expected — push rejected due to quota
          }

          // Wait for webhook with quota_error event
          const webhook = await receiver.waitForWebhook(undefined, 60_000);
          expect(webhook).not.toBeNull();
          expect(webhook?.body).toHaveProperty('namespace');
          expect(webhook?.body).toHaveProperty('threshold_percent');
        } finally {
          await receiver.stop();
        }
      },
    );

    test(
      'email notification fires on quota threshold crossing',
      {
        tag: [
          '@feature:QUOTA_MANAGEMENT',
          '@feature:EDIT_QUOTA',
          '@feature:MAILING',
          '@container',
          '@superuser',
        ],
      },
      async ({api, superuserApi}) => {
        test.setTimeout(300_000);

        const contactEmail = 'quota-warn-test@example.com';
        const org = await api.organization('nsdelivemail', contactEmail);

        // Set up quota (3 MiB) with warning limit at 80%
        const quota = await superuserApi.quota(org.name, 3145728);
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Warning',
          80,
        );

        // Create email notification for quota_warning
        await api.namespaceNotification(
          org.name,
          'quota_warning',
          'email',
          {email: contactEmail},
          {},
          'Email Warning',
        );

        // Clear inbox before push
        await mailpit.clearInbox();

        // Push pinned UBI to exceed warning threshold
        await api.repositoryWithName(org.name, 'emailrepo1');
        await api.repositoryWithName(org.name, 'emailrepo2');
        await pushQuotaNotificationImage(
          org.name,
          'emailrepo1',
          'v1',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );
        await pushQuotaNotificationImage(
          org.name,
          'emailrepo2',
          'v2',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Wait for email
        const email = await mailpit.waitForEmail(
          (msg) =>
            msg.To.some((to) => to.Address === contactEmail) &&
            (msg.Subject.includes('quota') ||
              msg.Subject.includes('Quota') ||
              msg.Subject.includes('warning') ||
              msg.Subject.includes('Warning')),
          30_000,
        );
        expect(email).not.toBeNull();
      },
    );

    test(
      'email notification falls back to org admin emails when no valid org email',
      {
        tag: [
          '@feature:QUOTA_MANAGEMENT',
          '@feature:EDIT_QUOTA',
          '@feature:MAILING',
          '@container',
          '@superuser',
        ],
      },
      async ({api, superuserApi}) => {
        test.setTimeout(300_000);

        // Create org WITHOUT explicit email (UUID placeholder used)
        const org = await api.organization('nsdelivfb');

        // Set up quota (3 MiB) with warning limit at 80%
        const quota = await superuserApi.quota(org.name, 3145728);
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Warning',
          80,
        );

        // Create email notification for quota_warning
        await api.namespaceNotification(
          org.name,
          'quota_warning',
          'email',
          {email: TEST_USERS.user.email},
          {},
          'Fallback Email',
        );

        // Clear inbox before push
        await mailpit.clearInbox();

        // Push images to exceed warning threshold (~1.4 MiB each)
        await api.repositoryWithName(org.name, 'fbrepo1');
        await api.repositoryWithName(org.name, 'fbrepo2');
        await pushQuotaNotificationImage(
          org.name,
          'fbrepo1',
          'v1',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );
        await pushQuotaNotificationImage(
          org.name,
          'fbrepo2',
          'v2',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Email should be delivered to org admin (testuser) email
        const email = await mailpit.waitForEmail(
          (msg) =>
            msg.To.some((to) => to.Address === TEST_USERS.user.email) &&
            (msg.Subject.includes('quota') || msg.Subject.includes('Quota')),
          30_000,
        );
        expect(email).not.toBeNull();
      },
    );

    test(
      'test notification button fires a webhook delivery',
      {tag: '@webhook'},
      async ({api}) => {
        test.setTimeout(60_000);

        const org = await api.organization('nsdelivtest');

        // Start webhook receiver
        const receiver = new WebhookReceiver();
        await receiver.start();
        try {
          // Create webhook notification via API
          const notification = await api.namespaceNotification(
            org.name,
            'quota_warning',
            'webhook',
            {url: receiver.getUrl()},
            {},
            'Test Button Webhook',
          );

          // Fire test notification via API
          await api.raw.testNamespaceNotification(org.name, notification.uuid);

          // Verify webhook received
          const webhook = await receiver.waitForWebhook(undefined, 30_000);
          expect(webhook).not.toBeNull();
        } finally {
          await receiver.stop();
        }
      },
    );

    test(
      'test notification payload includes formatted byte fields (PROJQUAY-12369)',
      {tag: '@webhook'},
      async ({api}) => {
        test.setTimeout(60_000);

        const org = await api.organization('nsdelivfmt');

        const receiver = new WebhookReceiver();
        await receiver.start();
        try {
          // Test quota_warning sample data
          const warnNotif = await api.namespaceNotification(
            org.name,
            'quota_warning',
            'webhook',
            {url: receiver.getUrl()},
            {},
            'Format Check Warning',
          );
          await api.raw.testNamespaceNotification(org.name, warnNotif.uuid);

          const warnHook = await receiver.waitForWebhook(undefined, 30_000);
          expect(warnHook).not.toBeNull();
          expect(warnHook?.body).toHaveProperty('usage_bytes_formatted');
          expect(warnHook?.body).toHaveProperty('limit_bytes_formatted');
          expect(warnHook?.body.usage_bytes_formatted).toBe('819.20 MB');
          expect(warnHook?.body.limit_bytes_formatted).toBe('1.00 GB');
        } finally {
          await receiver.stop();
        }
      },
    );

    test(
      'retroactive webhook fires when quota limit is created while already exceeded',
      {
        tag: [
          '@feature:QUOTA_MANAGEMENT',
          '@feature:EDIT_QUOTA',
          '@container',
          '@superuser',
          '@webhook',
        ],
      },
      async ({api, superuserApi}) => {
        test.setTimeout(300_000);

        const org = await api.organization('nsdelivretro');

        // Push pinned UBI before quota is configured
        await api.repositoryWithName(org.name, 'retrorepo1');
        await pushQuotaNotificationImage(
          org.name,
          'retrorepo1',
          'v1',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Start webhook receiver
        const receiver = new WebhookReceiver();
        await receiver.start();
        try {
          // Create webhook notification for quota_warning
          await api.namespaceNotification(
            org.name,
            'quota_warning',
            'webhook',
            {url: receiver.getUrl()},
            {},
            'Retroactive Webhook',
          );

          // NOW set quota (3 MiB) with warning limit at 80% — usage already exceeds threshold
          const quota = await superuserApi.quota(org.name, 3145728);
          await superuserApi.raw.createQuotaLimit(
            org.name,
            quota.quotaId,
            'Warning',
            80,
          );

          // Webhook should fire retroactively
          const webhook = await receiver.waitForWebhook(undefined, 60_000);
          expect(webhook).not.toBeNull();
          expect(webhook?.body).toHaveProperty('namespace');
          expect(webhook?.body).toHaveProperty('threshold_percent');
        } finally {
          await receiver.stop();
        }
      },
    );
  },
);
