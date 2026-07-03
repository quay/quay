import fs from 'fs';
import path from 'path';

import {expect, test, uniqueName} from '../../fixtures';

const repoRoot = path.resolve(__dirname, '../../../..');

test.describe(
  'Repository spam detection ingress',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('image build context carries the baked classifier artifact path', async () => {
      const configPy = fs.readFileSync(
        path.join(repoRoot, 'config.py'),
        'utf8',
      );
      const dockerfile = fs.readFileSync(
        path.join(repoRoot, 'Dockerfile'),
        'utf8',
      );
      const dockerignore = fs.readFileSync(
        path.join(repoRoot, '.dockerignore'),
        'utf8',
      );

      expect(configPy).toContain(
        'SPAM_DETECTION_CLASSIFIER_PATH = "/conf/spam-detection/classifier.json"',
      );
      expect(dockerfile).toContain('COPY --chown=0:0 . .');
      expect(dockerfile).toContain('ln -s $QUAYCONF /conf');
      expect(dockerignore).not.toMatch(/^conf\/spam-detection(?:\/\*\*)?$/m);
    });

    test('allows repository description create and update when disabled', async ({
      adminClient,
      superuserApi,
    }) => {
      const org = await superuserApi.organization('spaming');
      const repoName = uniqueName('spamrepo');
      const description = 'free casino bonus crypto gift cards click now';

      const create = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: repoName,
        description,
      });
      expect(create.status()).toBe(201);

      const created = await adminClient.get(
        `/api/v1/repository/${org.name}/${repoName}`,
      );
      expect(created.status()).toBe(200);
      expect((await created.json()).description).toBe(description);

      const updatedDescription = `${description} updated`;
      const update = await adminClient.put(
        `/api/v1/repository/${org.name}/${repoName}`,
        {
          description: updatedDescription,
        },
      );
      expect(update.status()).toBe(200);

      const updated = await adminClient.get(
        `/api/v1/repository/${org.name}/${repoName}`,
      );
      expect(updated.status()).toBe(200);
      expect((await updated.json()).description).toBe(updatedDescription);
    });

    test('rejects spam repository descriptions when enforcement is enabled', async ({
      adminClient,
      superuserApi,
      quayConfig,
    }) => {
      test.skip(
        quayConfig.features?.SPAM_DETECTION !== true ||
          quayConfig.config?.SPAM_DETECTION_DRY_RUN !== false ||
          quayConfig.config?.SPAM_DETECTION_CLASSIFIER_VERSION !== 'e2e-v1',
        'Requires FEATURE_SPAM_DETECTION=true, SPAM_DETECTION_DRY_RUN=false, and the e2e-v1 classifier artifact',
      );
      expect(quayConfig.config?.SPAM_DETECTION_CLASSIFIER_PATH).toBeTruthy();

      const org = await superuserApi.organization('spamingress');
      const spamRepoName = uniqueName('spamrepo');
      const hamRepoName = uniqueName('hamrepo');

      const rejected = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: spamRepoName,
        description: 'free casino bonus crypto gift cards click now',
      });
      expect(rejected.status()).toBe(400);

      const allowed = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: hamRepoName,
        description: 'trusted base image for python applications',
      });
      expect(allowed.status()).toBe(201);

      const update = await adminClient.put(
        `/api/v1/repository/${org.name}/${hamRepoName}`,
        {
          description: 'free casino bonus crypto gift cards click now',
        },
      );
      expect(update.status()).toBe(400);
    });
  },
);
