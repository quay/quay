/**
 * Build API Guard Tests
 *
 * Covers the guards on build cancellation (DELETE .../build/<uuid>) and on
 * the custom-git trigger webhook (POST /webhooks/push/trigger/<uuid>).
 */

import {test, expect, getTestUsers} from '../../fixtures';
import {API_URL} from '../../utils/config';

test.describe(
  'Build API Guards',
  {tag: ['@api', '@auth:Database', '@feature:BUILD_SUPPORT']},
  () => {
    test(
      'cancel build rejects a uuid from another repo and a non-admin writer',
      {tag: '@superuser'},
      async ({superuserApi, adminClient, userClient, cachedQuayConfig}) => {
        const org = await superuserApi.organization('buildcancel');
        const repo = await superuserApi.repository(org.name, 'owner');
        const other = await superuserApi.repository(org.name, 'other');
        const build = await superuserApi.build(org.name, repo.name);
        const writer = getTestUsers(cachedQuayConfig).user.username;
        await superuserApi.repositoryPermission(
          org.name,
          repo.name,
          'user',
          writer,
          'write',
        );

        // Cancel requires repo admin; write is not enough.
        const writerGet = await userClient.get(
          `/api/v1/repository/${repo.fullName}/build/${build.buildId}`,
        );
        expect(writerGet.status()).toBe(200);
        const writerCancel = await userClient.delete(
          `/api/v1/repository/${repo.fullName}/build/${build.buildId}`,
        );
        expect(writerCancel.status()).toBe(403);

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
        expect((await stillThere.json()).phase).not.toBe('cancelled');
      },
    );

    test(
      'custom-git webhook checks credentials and payload, then queues a build',
      {tag: '@superuser'},
      async ({superuserApi, request}) => {
        const org = await superuserApi.organization('webhook');
        const repo = await superuserApi.repository(org.name, 'customgit');
        const triggerUuid = await superuserApi.raw.createCustomGitTrigger(
          org.name,
          repo.name,
        );
        await superuserApi.raw.activateTrigger(
          org.name,
          repo.name,
          triggerUuid,
          {
            build_source: 'https://github.com/quay/quay',
            dockerfile_path: '/Dockerfile',
            context: '/',
          },
        );

        const {triggers} = await superuserApi.raw.listTriggers(
          org.name,
          repo.name,
        );
        const trigger = triggers.find((t) => t.id === triggerUuid) as {
          config: {credentials: {name: string; value: string}[]};
        };
        const hook = trigger.config.credentials.find(
          (c) => c.name === 'Webhook Endpoint URL',
        );
        expect(hook).toBeDefined();
        const webhook = new URL(hook?.value ?? '');
        const url = `${API_URL}${webhook.pathname}`;
        const basic = (user: string, pass: string) => ({
          Authorization: `Basic ${Buffer.from(`${user}:${pass}`).toString(
            'base64',
          )}`,
        });
        const valid = basic(
          decodeURIComponent(webhook.username),
          decodeURIComponent(webhook.password),
        );
        const payload = {
          commit: '1c002dd3a9f84a8b3c7e5e2a9d5f1e0b4c6d8e7f',
          ref: 'refs/heads/master',
          default_branch: 'master',
        };

        const noAuth = await request.post(url, {data: payload});
        expect(noAuth.status()).toBe(403);

        const wrongAuth = await request.post(url, {
          headers: basic('$token', 'not-the-trigger-token'),
          data: payload,
        });
        expect(wrongAuth.status()).toBe(403);

        const badPayload = await request.post(url, {
          headers: valid,
          data: {commit: 'not-a-sha', ref: 'main'},
        });
        expect(badPayload.status()).toBe(400);

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
