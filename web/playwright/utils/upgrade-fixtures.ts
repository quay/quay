/**
 * Shared, DETERMINISTIC fixtures for the operator-upgrade lane.
 *
 * Unlike the rest of the suite, upgrade specs run as two independent Playwright
 * invocations (seed on n-1, verify on n) that communicate ONLY through persisted
 * Quay server state (Postgres rows + S3 blobs). Names must therefore be fixed and
 * identical on both sides — do NOT use uniqueName(). Each CI run gets a fresh
 * cluster, so fixed names never collide across runs.
 *
 * See e2e/upgrade/upgrade-seed.spec.ts and e2e/upgrade/upgrade-verify.spec.ts.
 */
export const UPGRADE = {
  org: 'upgrade-persist-org',
  repo: 'upgrade-persist-repo', // full: upgrade-persist-org/upgrade-persist-repo
  robotShortname: 'upgradebot', // full robot name: upgrade-persist-org+upgradebot
  team: 'upgradeteam',
  user: {
    username: 'upgradeuser',
    password: 'password',
    email: 'upgradeuser@example.com',
  },
  imageTag: 'v1-pre-upgrade',
  // A second tag pointing at the SAME single-arch manifest, to prove multiple
  // tag->manifest rows survive the upgrade.
  imageTagAlias: 'v1-pre-upgrade-alias',
  // A multi-arch manifest list, to prove the manifest-list -> child-manifest
  // join (ManifestChild) survives the upgrade.
  multiArchTag: 'v1-multiarch',
  // An OCI referrer (SBOM) attached to the single-arch image via oras, to prove
  // the referrers index survives the upgrade. The fixture file shipped at
  // web/playwright/fixtures/oras/referrer.spdx.json is attached with this type.
  sbomArtifactType: 'application/spdx+json',
} as const;
