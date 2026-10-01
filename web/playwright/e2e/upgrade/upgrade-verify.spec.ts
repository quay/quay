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
 * cherry-picked byte-identical across master (3.19) and redhat-3.18/3.17/3.16.
 * See utils/upgrade-fixtures.ts.
 */

import {test, expect} from '../../fixtures';
import {UPGRADE} from '../../utils/upgrade-fixtures';
import {pullImage, orasDiscover, isOrasAvailable} from '../../utils/container';

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
  },
);
