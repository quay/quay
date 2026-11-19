/**
 * Build API Guard Tests
 *
 * Covers the guards on build cancellation (DELETE .../build/<uuid>) and on
 * the custom-git trigger webhook (POST /webhooks/push/trigger/<uuid>).
 */

import {test, expect, getTestUsers, TestApi} from '../../fixtures';
import {API_URL} from '../../utils/config';

const basic = (user: string, pass: string) => ({
  Authorization: `Basic ${Buffer.from(`${user}:${pass}`).toString('base64')}`,
});

const payload = {
  commit: '1c002dd3a9f84a8b3c7e5e2a9d5f1e0b4c6d8e7f',
  ref: 'refs/heads/master',
  default_branch: 'master',
};

async function customGitWebhook(superuserApi: TestApi) {
  const org = await superuserApi.organization('webhook');
  const repo = await superuserApi.repository(org.name, 'customgit');
  const triggerUuid = await superuserApi.raw.createCustomGitTrigger(
    org.name,
    repo.name,
  );
  await superuserApi.raw.activateTrigger(org.name, repo.name, triggerUuid, {
    build_source: 'https://github.com/quay/quay',
    dockerfile_path: '/Dockerfile',
    context: '/',
  });

  const {triggers} = await superuserApi.raw.listTriggers(org.name, repo.name);
  const trigger = triggers.find((t) => t.id === triggerUuid) as {
    config: {credentials: {name: string; value: string}[]};
  };
  const hook = trigger.config.credentials.find(
    (c) => c.name === 'Webhook Endpoint URL',
  );
  expect(hook).toBeDefined();
  const webhook = new URL(hook?.value ?? '');
  const user = decodeURIComponent(webhook.username);
  const token = decodeURIComponent(webhook.password);
  // The token is a 32-char lookup name then the secret (data/model/token.py),
  // so this one finds the trigger's token and fails only the secret check.
  const wrongSecret = token.slice(0, 32) + 'x'.repeat(token.length - 32);
  return {
    org,
    repo,
    triggerUuid,
    url: `${API_URL}${webhook.pathname}`,
    valid: basic(user, token),
    wrong: basic(user, wrongSecret),
  };
}

test.describe(
  'Build API Guards',
  {tag: ['@api', '@auth:Database', '@feature:BUILD_SUPPORT']},
  () => {
    test(
      'cancel build rejects a non-admin writer',
      {tag: '@superuser'},
      async ({superuserApi, adminClient, userClient, cachedQuayConfig}) => {
        const org = await superuserApi.organization('buildcancel');
        const repo = await superuserApi.repository(org.name, 'owner');
        const build = await superuserApi.build(org.name, repo.name);
        const writer = getTestUsers(cachedQuayConfig).user.username;
        await superuserApi.repositoryPermission(
          org.name,
          repo.name,
          'user',
          writer,
          'write',
        );
        const buildPath = `/api/v1/repository/${repo.fullName}/build/${build.buildId}`;

        // Cancel requires repo admin; write is not enough.
        const writerGet = await userClient.get(buildPath);
        expect(writerGet.status()).toBe(200);
        expect((await writerGet.json()).is_writer).toBe(true);
        const writerCancel = await userClient.delete(buildPath);
        expect(writerCancel.status()).toBe(403);

        const stillThere = await adminClient.get(buildPath);
        expect(stillThere.status()).toBe(200);
        const {phase} = await stillThere.json();
        expect(typeof phase).toBe('string');
        expect(phase).not.toBe('cancelled');
      },
    );

    test(
      'cancel build rejects a build uuid from another repo',
      {tag: '@superuser'},
      async ({superuserApi, adminClient}) => {
        const org = await superuserApi.organization('buildcancel');
        const repo = await superuserApi.repository(org.name, 'owner');
        const other = await superuserApi.repository(org.name, 'other');
        const build = await superuserApi.build(org.name, repo.name);

        // An admin of both repos still cannot cancel the build through the
        // repo that does not own it.
        const crossRepoCancel = await adminClient.delete(
          `/api/v1/repository/${other.fullName}/build/${build.buildId}`,
        );
        expect(crossRepoCancel.status()).toBe(404);

        const stillThere = await adminClient.get(
          `/api/v1/repository/${repo.fullName}/build/${build.buildId}`,
        );
        expect(stillThere.status()).toBe(200);
        const {phase} = await stillThere.json();
        expect(typeof phase).toBe('string');
        expect(phase).not.toBe('cancelled');
      },
    );

    test(
      'custom-git webhook rejects missing credentials',
      {tag: '@superuser'},
      async ({superuserApi, request}) => {
        const {org, repo, url} = await customGitWebhook(superuserApi);
        const resp = await request.post(url, {data: payload});
        expect(resp.status()).toBe(403);
        const {builds} = await superuserApi.raw.getBuilds(org.name, repo.name);
        expect(builds).toHaveLength(0);
      },
    );

    test(
      'custom-git webhook rejects wrong credentials',
      {tag: '@superuser'},
      async ({superuserApi, request}) => {
        const {org, repo, url, wrong} = await customGitWebhook(superuserApi);
        const resp = await request.post(url, {headers: wrong, data: payload});
        expect(resp.status()).toBe(403);
        const {builds} = await superuserApi.raw.getBuilds(org.name, repo.name);
        expect(builds).toHaveLength(0);
      },
    );

    test(
      'custom-git webhook rejects an invalid commit',
      {tag: '@superuser'},
      async ({superuserApi, request}) => {
        const {org, repo, url, valid} = await customGitWebhook(superuserApi);
        const resp = await request.post(url, {
          headers: valid,
          data: {...payload, commit: 'not-a-sha'},
        });
        expect(resp.status()).toBe(400);
        const {builds} = await superuserApi.raw.getBuilds(org.name, repo.name);
        expect(builds).toHaveLength(0);
      },
    );

    test(
      'custom-git webhook rejects an invalid ref',
      {tag: '@superuser'},
      async ({superuserApi, request}) => {
        const {org, repo, url, valid} = await customGitWebhook(superuserApi);
        const resp = await request.post(url, {
          headers: valid,
          data: {...payload, ref: 'main'},
        });
        expect(resp.status()).toBe(400);
        const {builds} = await superuserApi.raw.getBuilds(org.name, repo.name);
        expect(builds).toHaveLength(0);
      },
    );

    test(
      'custom-git webhook queues a build',
      {tag: '@superuser'},
      async ({superuserApi, request}) => {
        const {org, repo, triggerUuid, url, valid} =
          await customGitWebhook(superuserApi);
        const ok = await request.post(url, {headers: valid, data: payload});
        expect(ok.status()).toBe(200);

        const builds = await superuserApi.raw.getBuilds(org.name, repo.name);
        expect(builds.builds).toHaveLength(1);
        expect(builds.builds[0]).toMatchObject({
          trigger: {id: triggerUuid},
          trigger_metadata: {commit: payload.commit, ref: payload.ref},
        });
      },
    );
  },
);
