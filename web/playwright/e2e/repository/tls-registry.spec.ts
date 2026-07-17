import {test} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage, pullImage, isSkopeoAvailable} from '../../utils/container';

const TLS_REGISTRY_URL = 'https://localhost:8443';

test.describe(
  'TLS registry interoperability',
  {tag: ['@container', '@repository', '@PROJQUAY-11484']},
  () => {
    test('pushes and pulls through the configured TLS listener', async ({
      api,
      containerAvailable,
    }) => {
      test.skip(!containerAvailable, 'registry image tooling required');
      test.skip(!(await isSkopeoAvailable()), 'skopeo CLI required');

      const repo = await api.repository();
      const {username, password} = TEST_USERS.user;

      await pushImage(
        repo.namespace,
        repo.name,
        'tls-check',
        username,
        password,
        {
          registryUrl: TLS_REGISTRY_URL,
        },
      );
      await pullImage(
        repo.namespace,
        repo.name,
        'tls-check',
        username,
        password,
        {
          registryUrl: TLS_REGISTRY_URL,
        },
      );
    });
  },
);
