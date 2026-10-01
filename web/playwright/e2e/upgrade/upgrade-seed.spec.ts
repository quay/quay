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
 * master (3.19) and redhat-3.18/3.17/3.16. See utils/upgrade-fixtures.ts.
 */

import * as path from 'path';
import {test, expect} from '../../fixtures';
import {UPGRADE} from '../../utils/upgrade-fixtures';
import {
  pushImage,
  pushMultiArchImage,
  orasAttach,
  orasDiscover,
  isOrasAvailable,
} from '../../utils/container';

test.describe(
  'Upgrade seed',
  {tag: ['@api', '@upgrade-seed', '@auth:Database']},
  () => {
    // 201 = created; 400/409 = already exists on a retry — both acceptable.
    const created = (r: {status(): number}) =>
      expect([201, 400, 409]).toContain(r.status());

    // Relationship/linkage writes (team membership, repo permission) return 200
    // on first write and stay idempotent on retry; 400/409 covers races.
    const linked = (r: {status(): number}) =>
      expect([200, 201, 400, 409]).toContain(r.status());

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

      // Relationship data — the rows most likely to be disturbed by a schema
      // migration. Add the seeded user to the team (user<->team join) ...
      linked(
        await adminClient.put(
          `/api/v1/organization/${UPGRADE.org}/team/${UPGRADE.team}/members/${UPGRADE.user.username}`,
        ),
      );
      // ... and grant the team write on the repo (team<->repo permission join).
      linked(
        await adminClient.put(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/permissions/team/${UPGRADE.team}`,
          {role: 'write'},
        ),
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
        const tags = (await tag.json()).tags as Array<{
          name: string;
          manifest_digest: string;
        }>;
        expect(tags.map((t) => t.name)).toContain(UPGRADE.imageTag);

        // Point a second tag at the same manifest so the upgrade must preserve
        // multiple tag->manifest rows, not just one.
        const digest = tags[0].manifest_digest;
        const alias = await adminClient.put(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/tag/${UPGRADE.imageTagAlias}`,
          {manifest_digest: digest},
        );
        expect([201, 200]).toContain(alias.status());
      },
    );

    // Multi-arch push: exercises survival of the manifest-list -> child-manifest
    // join (ManifestChild), the relationship most exposed to schema migrations.
    // @container-gated (skopeo); kept separate so the single-arch push still runs.
    test(
      'seeds a multi-arch image whose child manifests must survive upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
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

        await pushMultiArchImage(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.multiArchTag,
          'admin',
          'password',
        );

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
        expect(manifestDigest).toBeTruthy();

        // Confirm it is really a manifest list with children before the upgrade.
        const manifest = await adminClient.get(
          `/api/v1/repository/${UPGRADE.org}/${UPGRADE.repo}/manifest/${manifestDigest}`,
        );
        expect(manifest.status()).toBe(200);
        expect((await manifest.json()).is_manifest_list).toBe(true);
      },
    );

    // Attaches an OCI referrer (SBOM) to the single-arch image via oras, so the
    // upgrade must preserve the referrers index (subject -> referrer links).
    // @container gates on skopeo; oras is additionally required, so skip when it
    // is absent. isOrasAvailable() is the only extra tooling gate in this file.
    test(
      'seeds an OCI referrer that must survive upgrade',
      {tag: ['@container']},
      async ({adminClient}) => {
        test.skip(
          !(await isOrasAvailable()),
          'oras CLI required for referrer tests',
        );

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

        // The referrer needs a subject manifest; ensure the single-arch image is
        // present (idempotent re-push of the same content).
        await pushImage(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.imageTag,
          'admin',
          'password',
        );

        orasAttach(
          UPGRADE.org,
          UPGRADE.repo,
          UPGRADE.imageTag,
          'admin',
          'password',
          UPGRADE.sbomArtifactType,
          'producer=quay-upgrade-e2e',
          path.join(__dirname, '../../fixtures/oras/referrer.spdx.json'),
        );

        // Sanity: the referrer is discoverable before the upgrade.
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
