import {test, expect} from '../../fixtures';

test.describe(
  'Mirror incremental sync (PROJQUAY-13193)',
  {tag: ['@api', '@feature:REPO_MIRROR']},
  () => {
    test('second sync preserves tag digest and completes without error', async ({
      api,
    }) => {
      // This test validates that the incremental sync optimization works
      // correctly: a second sync of an unchanged tag should succeed and
      // leave the manifest digest identical to the first sync.
      test.setTimeout(300_000);

      const org = await api.organization('incrsyncorg');
      const repo = await api.repository(org.name, 'incrsyncrepo');
      const robot = await api.robot(org.name, 'incrsyncbot');
      await api.setMirrorState(org.name, repo.name);

      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createMirrorConfig(org.name, repo.name, {
        external_reference: 'quay.io/quay/busybox',
        sync_interval: 86400,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['latest']},
        robot_username: robot.fullName,
        skopeo_timeout_interval: 300,
        is_enabled: true,
        verify_tls: true,
      });

      // --- First sync ---
      await api.raw.triggerMirrorSync(org.name, repo.name);

      await expect
        .poll(
          async () => {
            const cfg = await api.raw.getMirrorConfig(org.name, repo.name);
            const status = cfg?.sync_status ?? 'UNKNOWN';
            if (status === 'FAIL') {
              throw new Error('First mirror sync failed');
            }
            return status;
          },
          {
            timeout: 120_000,
            intervals: [5_000, 10_000, 15_000],
            message: 'First sync did not complete within 2 minutes',
          },
        )
        .toBe('SUCCESS');

      const tagsAfterFirst = await api.raw.getTags(org.name, repo.name);
      const firstDigest = tagsAfterFirst.tags.find(
        (t) => t.name === 'latest',
      )?.manifest_digest;
      expect(firstDigest).toBeTruthy();

      // --- Second sync (should skip the unchanged tag) ---
      await api.raw.triggerMirrorSync(org.name, repo.name);

      await expect
        .poll(
          async () => {
            const cfg = await api.raw.getMirrorConfig(org.name, repo.name);
            const status = cfg?.sync_status ?? 'UNKNOWN';
            if (status === 'FAIL') {
              throw new Error('Second mirror sync failed');
            }
            return status;
          },
          {
            timeout: 120_000,
            intervals: [5_000, 10_000, 15_000],
            message: 'Second sync did not complete within 2 minutes',
          },
        )
        .toBe('SUCCESS');

      // Verify the tag digest is unchanged after the second sync
      const tagsAfterSecond = await api.raw.getTags(org.name, repo.name);
      const secondDigest = tagsAfterSecond.tags.find(
        (t) => t.name === 'latest',
      )?.manifest_digest;
      expect(secondDigest).toBe(firstDigest);
    });
  },
);
