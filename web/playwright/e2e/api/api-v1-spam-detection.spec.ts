import {expect, test, uniqueName} from '../../fixtures';

test.describe(
  'Repository spam detection ingress',
  {tag: ['@api', '@auth:Database']},
  () => {
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
  },
);
