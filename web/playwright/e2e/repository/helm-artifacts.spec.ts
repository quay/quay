/**
 * Helm Chart OCI Artifact E2E Tests
 *
 * Pushes a chart with the real helm CLI, checks it in the repository UI and
 * the manifest API, and pulls it back with helm.
 *
 * @PROJQUAY-11451
 */

import {test, expect, getTestUsers} from '../../fixtures';
import {pullHelmChart, pushHelmChart} from '../../utils/container';

const HELM_CONFIG_TYPE = 'application/vnd.cncf.helm.config.v1+json';

test.describe(
  'Helm Chart OCI Artifacts',
  {tag: ['@repository', '@helm']},
  () => {
    test('helm push shows the tag in the UI and helm pull returns the same chart', async ({
      authenticatedPage,
      api,
      userClient,
      quayConfig,
    }) => {
      const user = getTestUsers(quayConfig).user;
      const repo = await api.repository(undefined, 'helmchart');

      const pushedSha256 = await pushHelmChart(
        repo.namespace,
        repo.name,
        '0.1.0',
        user.username,
        user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: '0.1.0'}),
      ).toBeVisible({timeout: 30000});

      const {tags} = await api.raw.getTags(repo.namespace, repo.name, {
        specificTag: '0.1.0',
      });
      const manifest = await userClient.get(
        `/api/v1/repository/${repo.fullName}/manifest/${tags[0].manifest_digest}`,
      );
      expect(manifest.status()).toBe(200);
      expect((await manifest.json()).config_media_type).toBe(HELM_CONFIG_TYPE);

      const pulledSha256 = await pullHelmChart(
        repo.namespace,
        repo.name,
        '0.1.0',
        user.username,
        user.password,
      );
      expect(pulledSha256).toBe(pushedSha256);
    });
  },
);
