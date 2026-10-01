/**
 * Operator-upgrade SEED spec (@upgrade-seed).
 *
 * Seeds deterministic data on the n-1 Quay server (e.g. 3.17) for the OLM
 * operator-upgrade lane. A separate invocation, @upgrade-verify, runs on the n
 * server (e.g. 3.18) AFTER the upgrade and asserts this data survived. The two
 * invocations share NO memory, env, or files — only persisted Quay server state
 * (Postgres rows + S3 blobs).
 *
 * This deliberately diverges from the suite's "NO DATABASE SEEDING / auto-cleanup"
 * convention (see AGENTS.md): it uses FIXED names (not uniqueName()) and the raw
 * adminClient (not the auto-cleanup `api` fixture) so the seeded objects SURVIVE to
 * the next invocation. It must NOT clean up. Each CI run is a fresh cluster, so the
 * fixed names never collide across runs; leaving data aids debugging.
 *
 * Idempotent: a retried step treats "already exists" (400/409) as success.
 *
 * Only version-tolerant, lowest-common-denominator behavior present in every
 * supported release is used, so the file is cherry-picked byte-identical across
 * master, redhat-3.18, and redhat-3.17. See utils/upgrade-fixtures.ts.
 */

import {test, expect} from '../../fixtures';
import {UPGRADE} from '../../utils/upgrade-fixtures';
import {pushImage} from '../../utils/container';

test.describe(
  'Upgrade seed',
  {tag: ['@api', '@upgrade-seed', '@auth:Database']},
  () => {
    // 201 = created; 400/409 = already exists on a retry — both acceptable.
    const created = (r: {status(): number}) =>
      expect([201, 400, 409]).toContain(r.status());

    test('seeds org, repo, robot, team, user that must survive upgrade', async ({
      adminClient,
    }) => {
      created(
        await adminClient.post('/api/v1/organization/', {
          name: UPGRADE.org,
          email: `${UPGRADE.org}@example.com`,
        }),
      );

      created(
        await adminClient.post('/api/v1/repository', {
          namespace: UPGRADE.org,
          repository: UPGRADE.repo,
          visibility: 'private',
          description: 'upgrade persistence repo',
          repo_kind: 'image',
        }),
      );

      created(
        await adminClient.put(
          `/api/v1/organization/${UPGRADE.org}/robots/${UPGRADE.robotShortname}`,
          {},
        ),
      );

      created(
        await adminClient.put(
          `/api/v1/organization/${UPGRADE.org}/team/${UPGRADE.team}`,
          {role: 'member'},
        ),
      );

      created(
        await adminClient.post('/api/v1/user/', {
          username: UPGRADE.user.username,
          password: UPGRADE.user.password,
          email: UPGRADE.user.email,
        }),
      );

      // Liveness sanity on the seeded state (minimal — NOT the functional suite).
      const repo = await adminClient.get(
        `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}`,
      );
      expect(repo.status()).toBe(200);
    });

    // Strongest proof of survival: pushes a blob so @upgrade-verify can pull it
    // post-upgrade, exercising S3 blob survival. Kept separate and @container-gated
    // so the API seed above still runs when skopeo is unavailable.
    test(
      'seeds an image whose blobs must survive upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
        // Ensure the org/repo exist even if the API-seed test did not run first.
        await adminClient.post('/api/v1/organization/', {
          name: UPGRADE.org,
          email: `${UPGRADE.org}@example.com`,
        });
        await adminClient.post('/api/v1/repository', {
          namespace: UPGRADE.org,
          repository: UPGRADE.repo,
          visibility: 'private',
          description: 'upgrade persistence repo',
          repo_kind: 'image',
        });

        await pushImage(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.imageTag,
          'admin',
          'password',
        );

        const tag = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/tag/?specificTag=${UPGRADE.imageTag}`,
        );
        expect(tag.status()).toBe(200);
        const names = ((await tag.json()).tags as Array<{name: string}>).map(
          (t) => t.name,
        );
        expect(names).toContain(UPGRADE.imageTag);
      },
    );
  },
);
