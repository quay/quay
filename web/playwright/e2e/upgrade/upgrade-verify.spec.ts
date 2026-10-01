/**
 * Operator-upgrade VERIFY spec (@upgrade-verify).
 *
 * Runs on the n Quay server (e.g. 3.18) AFTER the OLM operator upgrade. Reads the
 * deterministic names that @upgrade-seed created on the n-1 server (e.g. 3.17) and
 * asserts they survived the upgrade with intact content. This is a SEPARATE
 * Playwright invocation: it shares state with the seed ONLY through the Quay server
 * (Postgres rows + S3 blobs), never through memory, env, or files.
 *
 * Like the seed, this diverges from the suite's auto-cleanup convention (see
 * AGENTS.md): it reads fixed names via the raw adminClient and does NOT clean up.
 * Each CI run is a fresh cluster, so leaving data never collides and aids debugging.
 *
 * Only version-tolerant, lowest-common-denominator behavior is used so the file is
 * cherry-picked byte-identical across master, redhat-3.18, and redhat-3.17.
 * See utils/upgrade-fixtures.ts.
 */

import {test, expect} from '../../fixtures';
import {UPGRADE} from '../../utils/upgrade-fixtures';
import {pullImage} from '../../utils/container';

test.describe(
  'Upgrade verify',
  {tag: ['@api', '@upgrade-verify', '@auth:Database']},
  () => {
    test('org, repo, robot, team, user survived the upgrade', async ({
      adminClient,
    }) => {
      const org = await adminClient.get(`/api/v1/organization/${UPGRADE.org}`);
      expect(org.status()).toBe(200);
      expect((await org.json()).name).toBe(UPGRADE.org);

      const repo = await adminClient.get(
        `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}`,
      );
      expect(repo.status()).toBe(200);

      const robots = await adminClient.get(
        `/api/v1/organization/${UPGRADE.org}/robots`,
      );
      expect(robots.status()).toBe(200);
      const robotNames = (
        (await robots.json()).robots as Array<{name: string}>
      ).map((r) => r.name);
      expect(robotNames).toContain(`${UPGRADE.org}+${UPGRADE.robotShortname}`);

      const team = await adminClient.get(
        `/api/v1/organization/${UPGRADE.org}/team/${UPGRADE.team}/members`,
      );
      expect(team.status()).toBe(200);

      const user = await adminClient.get(
        `/api/v1/superuser/users/${UPGRADE.user.username}`,
      );
      expect(user.status()).toBe(200);
    });

    // Proves the blob @upgrade-seed pushed survived in S3 across the upgrade by
    // pulling it back. @container-gated so it auto-skips when skopeo is absent (and
    // when the seed's @container push did not run, there is nothing to pull).
    test(
      'seeded image blobs survived the upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
        const tag = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/tag/?specificTag=${UPGRADE.imageTag}`,
        );
        expect(tag.status()).toBe(200);
        const names = ((await tag.json()).tags as Array<{name: string}>).map(
          (t) => t.name,
        );
        test.skip(
          !names.includes(UPGRADE.imageTag),
          'Seed did not push an image (skopeo unavailable on the n-1 phase)',
        );

        await pullImage(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.imageTag,
          'admin',
          'password',
        );
      },
    );
  },
);
