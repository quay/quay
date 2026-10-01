/**
 * Operator-upgrade VERIFY spec (@upgrade-verify).
 *
 * Runs on the n Quay server (e.g. 3.18) AFTER the OLM operator upgrade. Reads the
 * deterministic names that @upgrade-seed created on the n-1 server (e.g. 3.17) and
 * asserts they survived the upgrade with intact content. This is a SEPARATE
 * Playwright invocation: it shares state with the seed ONLY through the Quay server
 * (Postgres rows + S3 blobs), never through memory, env, or files.
 *
 * Like the seed, this reads fixed names via the raw adminClient (not the suite's
 * auto-cleanup `api` fixture). The verify assertions themselves do NOT clean up; a
 * final, opt-out cleanup step (see below) removes the seed data once verification
 * passes, so a shared or local Quay instance can be reused by other suites without
 * the fixed-name fixtures colliding. On the real CI upgrade lane each run is a fresh
 * cluster, so cleanup is harmless there either way.
 *
 * This describe runs SERIAL so the final cleanup test runs strictly after all verify
 * assertions on one worker (fullyParallel would otherwise let cleanup race ahead and
 * delete the org mid-pull). Serial mode also means a failed verify assertion skips
 * cleanup, preserving the server state for debugging — only a clean pass tears down.
 *
 * Only version-tolerant, lowest-common-denominator behavior is used so the file is
 * cherry-picked byte-identical across master (3.19) and redhat-3.18/3.17/3.16.
 * See utils/upgrade-fixtures.ts.
 */

import {test, expect} from '../../fixtures';
import {UPGRADE} from '../../utils/upgrade-fixtures';
import {pullImage, orasDiscover, isOrasAvailable} from '../../utils/container';

// Post-verify cleanup is opt-out: it runs by default so other suites can reuse the
// instance. Set UPGRADE_CLEAN=0 (also false/no) to keep the seed data in place —
// e.g. to inspect server state after a run.
const cleanupEnabled = !['0', 'false', 'no'].includes(
  (process.env.UPGRADE_CLEAN ?? '').toLowerCase(),
);

test.describe(
  'Upgrade verify',
  {tag: ['@api', '@upgrade-verify', '@auth:Database']},
  () => {
    // Serial so the trailing cleanup test runs last, after every verify assertion.
    test.describe.configure({mode: 'serial'});

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
      const repoBody = await repo.json();
      // Metadata, not just existence, must survive the migration.
      expect(repoBody.name).toBe(UPGRADE.repo);
      expect(repoBody.is_public).toBe(false);
      expect(repoBody.description).toBe('upgrade persistence repo');

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
      // The user<->team membership join seeded on n-1 must survive.
      const memberNames = (
        (await team.json()).members as Array<{name: string}>
      ).map((m) => m.name);
      expect(memberNames).toContain(UPGRADE.user.username);

      // The team<->repo permission join seeded on n-1 must survive, role intact.
      const perm = await adminClient.get(
        `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/permissions/team/${UPGRADE.team}`,
      );
      expect(perm.status()).toBe(200);
      expect((await perm.json()).role).toBe('write');

      const user = await adminClient.get(
        `/api/v1/superuser/users/${UPGRADE.user.username}`,
      );
      expect(user.status()).toBe(200);
    });

    // Proves the blob @upgrade-seed pushed survived in S3 across the upgrade by
    // pulling it back, and that both tags pointing at that manifest survived.
    // @container-gated so it auto-skips when skopeo is absent (and when the seed's
    // @container push did not run, there is nothing to pull).
    test(
      'seeded image blobs and tags survived the upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
        const list = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/tag/`,
        );
        expect(list.status()).toBe(200);
        const names = ((await list.json()).tags as Array<{name: string}>).map(
          (t) => t.name,
        );
        test.skip(
          !names.includes(UPGRADE.imageTag),
          'Seed did not push an image (skopeo unavailable on the n-1 phase)',
        );

        // Both the primary tag and the alias pointing at the same manifest must
        // survive — proves multiple tag->manifest rows persisted.
        expect(names).toContain(UPGRADE.imageTag);
        expect(names).toContain(UPGRADE.imageTagAlias);

        await pullImage(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.imageTag,
          'admin',
          'password',
        );
      },
    );

    // Proves the multi-arch manifest list and its child manifests survived the
    // upgrade (ManifestChild join). Self-skips when the seed did not push it.
    test(
      'seeded multi-arch image survived the upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
        const tag = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/tag/?specificTag=${UPGRADE.multiArchTag}`,
        );
        expect(tag.status()).toBe(200);
        const manifestDigest = (
          (await tag.json()).tags as Array<{
            name: string;
            manifest_digest: string;
          }>
        ).find((t) => t.name === UPGRADE.multiArchTag)?.manifest_digest;
        test.skip(
          !manifestDigest,
          'Seed did not push a multi-arch image (skopeo unavailable on the n-1 phase)',
        );

        const manifest = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/manifest/${manifestDigest}`,
        );
        expect(manifest.status()).toBe(200);
        // The manifest list and its child-manifest relationships must persist.
        expect((await manifest.json()).is_manifest_list).toBe(true);

        // Pulling by the manifest-list tag reassembles the children from storage.
        await pullImage(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.multiArchTag,
          'admin',
          'password',
        );
      },
    );

    // Proves the OCI referrer (SBOM) attached on n-1 survived the upgrade: the
    // subject->referrer link in the referrers index must still resolve.
    // @container gates on skopeo; oras is additionally required.
    test(
      'seeded OCI referrer survived the upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
        test.skip(
          !(await isOrasAvailable()),
          'oras CLI required for referrer tests',
        );

        // Nothing to verify if the single-arch subject image was never seeded.
        const tag = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/tag/?specificTag=${UPGRADE.imageTag}`,
        );
        expect(tag.status()).toBe(200);
        const seeded = ((await tag.json()).tags as Array<{name: string}>).some(
          (t) => t.name === UPGRADE.imageTag,
        );
        test.skip(
          !seeded,
          'Seed did not push the subject image (skopeo unavailable on the n-1 phase)',
        );

        const types = await orasDiscover(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.imageTag,
          'admin',
          'password',
        );
        expect(types).toContain(UPGRADE.sbomArtifactType);
      },
    );

    // Final step: tear down everything @upgrade-seed created so other suites can
    // reuse this instance. Runs last (serial describe) and only after the verify
    // assertions above have passed. Opt out with UPGRADE_CLEAN=0.
    test('cleans up seed data after verify (set UPGRADE_CLEAN=0 to skip)', async ({
      adminClient,
    }) => {
      test.skip(!cleanupEnabled, 'UPGRADE_CLEAN disables post-verify cleanup');

      // 204 = deleted; 404 = already gone (idempotent re-run); 400 = a mark-for-
      // deletion already in flight. All three mean the object is gone.
      const removed = (r: {status(): number}) =>
        expect([204, 404, 400]).toContain(r.status());

      // Deleting the org marks its namespace for deletion, cascading the repository
      // (tags, manifests, referrers), robots, teams, and the team->repo permission,
      // and frees the fixed org/repo names immediately.
      removed(await adminClient.delete(`/api/v1/organization/${UPGRADE.org}`));

      // The standalone DB user lives outside the org namespace; remove it via the
      // superuser API.
      removed(
        await adminClient.delete(
          `/api/v1/superuser/users/${UPGRADE.user.username}`,
        ),
      );

      // The org name must be freed so a later seed (or other suite) can reuse it.
      const org = await adminClient.get(`/api/v1/organization/${UPGRADE.org}`);
      expect(org.status()).toBe(404);
    });
  },
);
