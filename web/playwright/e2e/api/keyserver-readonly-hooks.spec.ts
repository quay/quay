/**
 * PROJQUAY-6259: Keyserver readonly lifecycle hooks.
 *
 * Tests the keyserver endpoints that the operator uses during the
 * read-only lifecycle: service filtering on the existing GET endpoint
 * and the new /status endpoint.
 *
 * These endpoints are unauthenticated (consistent with the keyserver
 * blueprint), so all requests use the anonClient fixture.
 */

import {test, expect} from '../../fixtures';

test.describe(
  'Keyserver readonly hooks',
  {tag: ['@api', '@readonly', '@auth:Database']},
  () => {
    let createdKid: string | null = null;

    test.afterEach(async ({adminClient}) => {
      if (createdKid) {
        // Service keys created via the superuser API can be cleaned up.
        // If cleanup fails (key already gone), ignore.
        try {
          await adminClient.delete(
            `/api/v1/superuser/keys/${createdKid}`,
          );
        } catch {
          // ignore
        }
        createdKid = null;
      }
    });

    test('GET /keys/services/<service>/keys/<kid>/status returns 404 for unknown kid', async ({
      anonClient,
    }) => {
      const resp = await anonClient.get(
        '/keys/services/quay/keys/nonexistent-kid-12345/status',
      );
      expect(resp.status()).toBe(404);
    });

    test('GET /keys/services/<service>/keys/<kid>/status returns correct fields for existing key', async ({
      adminClient,
      anonClient,
    }) => {
      // Create a service key via the superuser API
      const createResp = await adminClient.post(
        '/api/v1/superuser/keys',
        {
          service: 'quay',
          expiration: null,
          notes: 'e2e test key for status endpoint',
        },
      );
      expect(createResp.status()).toBe(200);
      const createBody = await createResp.json();
      createdKid = createBody.kid;

      // Approve the key
      const approveResp = await adminClient.put(
        `/api/v1/superuser/keys/${createdKid}`,
      );
      // The approve endpoint may return 200 or 204
      expect([200, 204]).toContain(approveResp.status());

      // Now test the status endpoint
      const statusResp = await anonClient.get(
        `/keys/services/quay/keys/${createdKid}/status`,
      );
      expect(statusResp.status()).toBe(200);

      const body = await statusResp.json();
      expect(body.kid).toBe(createdKid);
      expect(body.service).toBe('quay');
      expect(typeof body.operator_managed).toBe('boolean');
      expect(body.operator_managed).toBe(false);
      expect(Object.keys(body).sort()).toEqual([
        'expiration_date',
        'kid',
        'operator_managed',
        'service',
      ]);
    });

    test('GET /keys/services/<wrong-service>/keys/<kid>/status returns 404 for wrong service', async ({
      adminClient,
      anonClient,
    }) => {
      const createResp = await adminClient.post(
        '/api/v1/superuser/keys',
        {
          service: 'quay',
          expiration: null,
          notes: 'e2e test key for wrong service check',
        },
      );
      expect(createResp.status()).toBe(200);
      const createBody = await createResp.json();
      createdKid = createBody.kid;

      const statusResp = await anonClient.get(
        `/keys/services/wrong-service/keys/${createdKid}/status`,
      );
      expect(statusResp.status()).toBe(404);
    });
  },
);
