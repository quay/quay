/**
 * Immutability Policy API tests.
 *
 * Ported from Cypress: quay_api_testing_all_new_ui.cy.js (lines 2289-2423).
 * Validates CRUD lifecycle for immutability policies at both
 * organization and repository levels.
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {getV2Token} from '../../utils/api/auth';
import {API_URL} from '../../utils/config';
import {isCraneAvailable, pushUniqueImage} from '../../utils/container';

const MANIFEST_ACCEPT = [
  'application/vnd.docker.distribution.manifest.v2+json',
  'application/vnd.oci.image.manifest.v1+json',
].join(', ');

test.describe(
  'Immutability Policies',
  {tag: ['@api', '@auth:Database', '@feature:IMMUTABLE_TAGS']},
  () => {
    test.describe('Organization immutability policies', () => {
      test(
        'create org immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
          const org = await superuserApi.organization('immut');

          const create = await adminClient.post(
            `/api/v1/organization/${org.name}/immutabilitypolicy/`,
            {tagPattern: 'stable*', tagPatternMatches: true},
          );
          expect(create.status()).toBe(201);
          const body = await create.json();
          expect(body.uuid).toBeTruthy();
        },
      );

      test(
        'get org immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
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
        },
      );

      test(
        'update org immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
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
        },
      );

      test(
        'delete org immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
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
        },
      );
    });

    test.describe('Repository immutability policies', () => {
      test(
        'create repo immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
          const org = await superuserApi.organization('immut_repo');
          const repo = await superuserApi.repository(
            org.name,
            'immut',
            'public',
          );

          const create = await adminClient.post(
            `/api/v1/repository/${repo.namespace}/${repo.name}/immutabilitypolicy/`,
            {tagPattern: 'latest*', tagPatternMatches: true},
          );
          expect(create.status()).toBe(201);
          const body = await create.json();
          expect(body.uuid).toBeTruthy();
        },
      );

      test(
        'get repo immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
          const org = await superuserApi.organization('immut_repo');
          const repo = await superuserApi.repository(
            org.name,
            'immut',
            'public',
          );
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
        },
      );

      test(
        'update repo immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
          const org = await superuserApi.organization('immut_repo');
          const repo = await superuserApi.repository(
            org.name,
            'immut',
            'public',
          );
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
        },
      );

      test(
        'delete repo immutability policy',
        {tag: '@superuser'},
        async ({adminClient, superuserApi}) => {
          const org = await superuserApi.organization('immut_repo');
          const repo = await superuserApi.repository(
            org.name,
            'immut',
            'public',
          );
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
        },
      );
    });
  },
);

test.describe(
  'Immutable tag enforcement',
  {tag: ['@api', '@auth:Database', '@feature:IMMUTABLE_TAGS', '@container']},
  () => {
    test('immutable tag refuses overwrite by push and by API retarget', async ({
      api,
      userClient,
      request,
    }) => {
      test.skip(!(await isCraneAvailable()), 'crane CLI required');

      const {username, password} = TEST_USERS.user;
      const org = await api.organization('immutenf');
      const repo = await api.repository(org.name, 'pinned');
      await pushUniqueImage(org.name, repo.name, 'pinned', username, password);
      await pushUniqueImage(org.name, repo.name, 'other', username, password);

      const digestOf = async (tag: string) => {
        const r = await userClient.get(
          `/api/v1/repository/${repo.fullName}/tag/?specificTag=${tag}&onlyActiveTags=true`,
        );
        expect(r.status()).toBe(200);
        const {tags} = await r.json();
        expect(tags).toHaveLength(1);
        return tags[0].manifest_digest as string;
      };
      const pinnedDigest = await digestOf('pinned');
      const otherDigest = await digestOf('other');
      expect(otherDigest).not.toBe(pinnedDigest);

      const tagPath = `/api/v1/repository/${repo.fullName}/tag/pinned`;
      expect((await userClient.put(tagPath, {immutable: true})).status()).toBe(
        201,
      );

      const v2Token = await getV2Token(
        request,
        API_URL,
        username,
        password,
        `repository:${repo.fullName}:pull,push`,
      );
      const authorization = `Bearer ${v2Token}`;
      const otherManifest = await request.get(
        `${API_URL}/v2/${repo.fullName}/manifests/${otherDigest}`,
        {headers: {authorization, Accept: MANIFEST_ACCEPT}},
      );
      expect(otherManifest.status()).toBe(200);
      const contentType = otherManifest.headers()['content-type'];
      const manifestBody = await otherManifest.body();
      const pushOtherAsPinned = () =>
        request.put(`${API_URL}/v2/${repo.fullName}/manifests/pinned`, {
          headers: {authorization, 'Content-Type': contentType},
          data: manifestBody,
        });

      const overwrite = await pushOtherAsPinned();
      expect(overwrite.status()).toBe(409);
      expect((await overwrite.json()).errors[0].code).toBe('TAG_IMMUTABLE');

      const retarget = await userClient.put(tagPath, {
        manifest_digest: otherDigest,
      });
      expect(retarget.status()).toBe(409);
      expect((await retarget.json()).error_type).toBe('tag_immutable');

      expect(await digestOf('pinned')).toBe(pinnedDigest);

      // Control: once the admin lifts immutability the same push lands, so
      // the 409s above came from immutability, not from a malformed request.
      expect((await userClient.put(tagPath, {immutable: false})).status()).toBe(
        201,
      );
      expect((await pushOtherAsPinned()).status()).toBe(201);
      expect(await digestOf('pinned')).toBe(otherDigest);
    });
  },
);
