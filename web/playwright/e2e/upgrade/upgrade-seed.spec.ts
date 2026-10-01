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
    // Serial: every seed test targets the SAME fixed-name org/repo (the names must
    // stay fixed so @upgrade-verify can find them, so unique-name isolation is not
    // an option). Running them in parallel races on first creation — concurrent
    // POSTs of the same repo return 500 and concurrent skopeo pushes fail blob
    // reuse with "authentication required". Serial execution creates the shared
    // org/repo once, then each subsequent test re-ensures it idempotently.
    test.describe.configure({mode: 'serial'});

    // Each seed write must either succeed (200 or 201 — the exact code varies by
    // endpoint: POST org/repo and PUT robot return 201, while PUT team and the
    // superuser user-create return 200) or be a harmless "already exists" on a
    // retry (400/409).
    const ok = (r: {status(): number}) =>
      expect([200, 201, 400, 409]).toContain(r.status());

    test('seeds org, repo, robot, team, user that must survive upgrade', async ({
      adminClient,
    }) => {
      ok(
        await adminClient.post('/api/v1/organization/', {
          name: UPGRADE.org,
          email: `${UPGRADE.org}@example.com`,
        }),
      );

      ok(
        await adminClient.post('/api/v1/repository', {
          namespace: UPGRADE.org,
          repository: UPGRADE.repo,
          visibility: 'private',
          description: 'upgrade persistence repo',
          repo_kind: 'image',
        }),
      );

      ok(
        await adminClient.put(
          `/api/v1/organization/${UPGRADE.org}/robots/${UPGRADE.robotShortname}`,
          {},
        ),
      );

      ok(
        await adminClient.put(
          `/api/v1/organization/${UPGRADE.org}/team/${UPGRADE.team}`,
          {role: 'member'},
        ),
      );

      // Create the standalone user via the SUPERUSER endpoint, not POST
      // /api/v1/user/. The public user-create path calls common_login and returns a
      // session cookie for the NEW user, which would hijack adminClient's admin
      // session (it shares one cookie jar) and make the team/permission writes below
      // run as the non-admin new user. The superuser endpoint creates the user with
      // no login side effect, so the admin session is preserved. (The generated
      // password is irrelevant here — verify never authenticates as this user.)
      ok(
        await adminClient.post('/api/v1/superuser/users/', {
          username: UPGRADE.user.username,
          email: UPGRADE.user.email,
        }),
      );

      // Relationship data — the rows most likely to be disturbed by a schema
      // migration. Add the seeded user to the team (user<->team join) ...
      ok(
        await adminClient.put(
          `/api/v1/organization/${UPGRADE.org}/team/${UPGRADE.team}/members/${UPGRADE.user.username}`,
        ),
      );
      // ... and grant the team write on the repo (team<->repo permission join).
      ok(
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
        // multiple tag->manifest rows, not just one. Match by name rather than
        // tags[0]: on a re-seed the alias tag may also be present and the response
        // order is not guaranteed.
        const digest = tags.find(
          (t) => t.name === UPGRADE.imageTag,
        )?.manifest_digest;
        expect(digest).toBeTruthy();
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
