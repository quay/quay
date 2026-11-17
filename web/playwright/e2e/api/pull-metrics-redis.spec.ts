/**
 * Exercises the registry pull path that writes pull metrics into Redis.
 *
 * Redis Cluster support is covered by Python unit/integration tests; this
 * e2e verifies the standalone Redis pull-metrics path still accepts pulls
 * end-to-end through the real registry API.
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pullImage, pushImage} from '../../utils/container';

test.describe(
  'Pull metrics Redis path',
  {tag: ['@api', '@container', '@auth:Database']},
  () => {
    test('push then pull writes through redis-backed pull metrics', async ({
      api,
    }) => {
      const org = await api.organization('pullmetrics');
      const repo = await api.repository(org.name, 'pullmetricsrepo');
      const tag = 'latest';
      const username = TEST_USERS.user.username;
      const password = TEST_USERS.user.password;

      await pushImage(org.name, repo.name, tag, username, password);
      await expect(
        pullImage(org.name, repo.name, tag, username, password),
      ).resolves.toBeUndefined();
    });
  },
);
