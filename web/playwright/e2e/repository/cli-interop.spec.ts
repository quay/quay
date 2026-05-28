import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {
  pushImage,
  isSkopeoAvailable,
  isRegctlAvailable,
  skopeoListTags,
  regctlListTags,
} from '../../utils/container';

test.describe(
  'CLI Interoperability',
  {tag: ['@container', '@repository']},
  () => {
    let orgName: string;
    let repoName: string;
    const tag = 'latest';
    const username = TEST_USERS.user.username;
    const password = TEST_USERS.user.password;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(120000);
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);

      orgName = username;
      repoName = `cli-interop-${Date.now()}`;
      await api.createRepository(orgName, repoName, 'private');

      await pushImage(orgName, repoName, tag, username, password);
    });

    test.afterAll(async ({userContext}) => {
      if (!repoName) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(orgName, repoName);
      } catch {
        // Ignore cleanup errors
      }
    });

    test('skopeo list-tags returns pushed tags (OCP-81035)', async () => {
      const available = await isSkopeoAvailable();
      test.skip(!available, 'skopeo CLI required');

      const tags = await skopeoListTags(orgName, repoName, username, password);
      expect(tags).toContain(tag);
    });

    test('regctl tag ls returns tags (OCP-81036)', async () => {
      const available = await isRegctlAvailable();
      test.skip(!available, 'regctl CLI required');

      const tags = await regctlListTags(orgName, repoName, username, password);
      expect(tags).toContain(tag);
    });
  },
);
