import {test, expect, getTestUsers} from '../../fixtures';
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
      async ({api, superuserApi, quayConfig}) => {
        test.setTimeout(300_000);
        const users = getTestUsers(quayConfig);

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
            users.user.username,
            users.user.password,
          );
          await pushQuotaNotificationImage(
            org.name,
            'deduprepo2',
            'v2',
            users.user.username,
            users.user.password,
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
            users.user.username,
            users.user.password,
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
