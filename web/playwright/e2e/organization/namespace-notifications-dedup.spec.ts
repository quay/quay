import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushQuotaNotificationImage} from '../../utils/container';
import {WebhookReceiver} from '../../utils/webhook';

test.describe(
  'Namespace Notifications — Dedup/Throttling',
  {
    tag: [
      '@organization',
      '@feature:QUOTA_NOTIFICATIONS',
      '@feature:QUOTA_MANAGEMENT',
      '@feature:EDIT_QUOTA',
      '@container',
    ],
  },
  () => {
    test(
      'duplicate push within cooldown does not fire second notification',
      {tag: ['@superuser', '@webhook']},
      async ({api, superuserApi}) => {
        test.setTimeout(300_000);

        const org = await api.organization('nsdedup');

        // Set up quota (5 MiB) with warning limit at 50% (~2.5 MiB threshold)
        const quota = await superuserApi.quota(org.name, 5242880);
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Warning',
          50,
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
            'Dedup Webhook',
          );

          // Push pinned UBI to cross the 50% threshold (~2.5 MiB of 5 MiB)
          await api.repositoryWithName(org.name, 'deduprepo1');
          await api.repositoryWithName(org.name, 'deduprepo2');
          await pushQuotaNotificationImage(
            org.name,
            'deduprepo1',
            'v1',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );
          await pushQuotaNotificationImage(
            org.name,
            'deduprepo2',
            'v2',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );

          // Wait for first webhook
          const firstWebhook = await receiver.waitForWebhook(undefined, 60_000);
          expect(firstWebhook).not.toBeNull();

          // Another upload while above threshold (within cooldown) — dedup should suppress
          await api.repositoryWithName(org.name, 'deduprepo3');
          await pushQuotaNotificationImage(
            org.name,
            'deduprepo3',
            'v3',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );

          // Wait 5 seconds — no additional webhook should arrive
          await new Promise((r) => setTimeout(r, 5000));

          // Should have received exactly 1 webhook (dedup suppressed the second)
          expect(receiver.getRequests()).toHaveLength(1);
        } finally {
          await receiver.stop();
        }
      },
    );
  },
);
