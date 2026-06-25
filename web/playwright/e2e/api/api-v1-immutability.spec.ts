/**
 * Immutability Policy API tests.
 *
 * Ported from Cypress: quay_api_testing_all_new_ui.cy.js (lines 2289-2423).
 * Validates CRUD lifecycle for immutability policies at both
 * organization and repository levels.
 */

import {test, expect} from '../../fixtures';

test.describe(
  'Immutability Policies',
  {tag: ['@api', '@auth:Database', '@feature:IMMUTABLE_TAGS']},
  () => {
    test.describe('Organization immutability policies', () => {
      test('create org immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut');

        const create = await adminClient.post(
          `/api/v1/organization/${org.name}/immutabilitypolicy/`,
          {tagPattern: 'stable*', tagPatternMatches: true},
        );
        expect(create.status()).toBe(201);
        const body = await create.json();
        expect(body.uuid).toBeTruthy();
      });

      test('get org immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut');
        const policy = await superuserApi.orgImmutabilityPolicy(
          org.name,
          'stable*',
        );

        const get = await adminClient.get(
          `/api/v1/organization/${org.name}/immutabilitypolicy/${policy.uuid}`,
        );
        expect(get.status()).toBe(200);
        const body = await get.json();
        expect(body.uuid).toBe(policy.uuid);
      });

      test('update org immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut');
        const policy = await superuserApi.orgImmutabilityPolicy(
          org.name,
          'stable*',
        );

        const update = await adminClient.put(
          `/api/v1/organization/${org.name}/immutabilitypolicy/${policy.uuid}`,
          {tagPattern: 'nightly*', tagPatternMatches: true},
        );
        expect(update.status()).toBe(204);

        const verify = await adminClient.get(
          `/api/v1/organization/${org.name}/immutabilitypolicy/${policy.uuid}`,
        );
        expect(verify.status()).toBe(200);
        const updated = await verify.json();
        expect(updated.tagPattern).toBe('nightly*');
        expect(updated.tagPatternMatches).toBe(true);
      });

      test('delete org immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut');
        const policy = await superuserApi.orgImmutabilityPolicy(
          org.name,
          'stable*',
        );

        const del = await adminClient.delete(
          `/api/v1/organization/${org.name}/immutabilitypolicy/${policy.uuid}`,
        );
        expect(del.status()).toBe(200);
        const body = await del.json();
        expect(body.uuid).toBe(policy.uuid);
      });
    });

    test.describe('Repository immutability policies', () => {
      test('create repo immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut_repo');
        const repo = await superuserApi.repository(org.name, 'immut', 'public');

        const create = await adminClient.post(
          `/api/v1/repository/${repo.namespace}/${repo.name}/immutabilitypolicy/`,
          {tagPattern: 'latest*', tagPatternMatches: true},
        );
        expect(create.status()).toBe(201);
        const body = await create.json();
        expect(body.uuid).toBeTruthy();
      });

      test('get repo immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut_repo');
        const repo = await superuserApi.repository(org.name, 'immut', 'public');
        const policy = await superuserApi.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'latest*',
        );

        const get = await adminClient.get(
          `/api/v1/repository/${repo.namespace}/${repo.name}/immutabilitypolicy/${policy.uuid}`,
        );
        expect(get.status()).toBe(200);
        const body = await get.json();
        expect(body.uuid).toBe(policy.uuid);
      });

      test('update repo immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut_repo');
        const repo = await superuserApi.repository(org.name, 'immut', 'public');
        const policy = await superuserApi.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'latest*',
        );

        const update = await adminClient.put(
          `/api/v1/repository/${repo.namespace}/${repo.name}/immutabilitypolicy/${policy.uuid}`,
          {tagPattern: 'stable*', tagPatternMatches: true},
        );
        expect(update.status()).toBe(204);

        const verify = await adminClient.get(
          `/api/v1/repository/${repo.namespace}/${repo.name}/immutabilitypolicy/${policy.uuid}`,
        );
        expect(verify.status()).toBe(200);
        const updated = await verify.json();
        expect(updated.tagPattern).toBe('stable*');
        expect(updated.tagPatternMatches).toBe(true);
      });

      test('delete repo immutability policy', async ({
        adminClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('immut_repo');
        const repo = await superuserApi.repository(org.name, 'immut', 'public');
        const policy = await superuserApi.repoImmutabilityPolicy(
          repo.namespace,
          repo.name,
          'latest*',
        );

        const del = await adminClient.delete(
          `/api/v1/repository/${repo.namespace}/${repo.name}/immutabilitypolicy/${policy.uuid}`,
        );
        expect(del.status()).toBe(200);
        const body = await del.json();
        expect(body.uuid).toBe(policy.uuid);
      });
    });
  },
);
