import {createHash} from 'crypto';
import {gzipSync} from 'zlib';
import {test, expect, getTestUsers} from '../../fixtures';
import {getV2Token} from '../../utils/api/auth';
import {API_URL} from '../../utils/config';

const OCI_MANIFEST = 'application/vnd.oci.image.manifest.v1+json';
const ARTIFACT_TYPE = 'application/vnd.quay.test.referrer';

function digest(bytes: Buffer): string {
  return `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
}

test.describe(
  'Digest deletion of OCI referrers',
  {tag: ['@api', '@v2', '@feature:REFERRERS_API']},
  () => {
    for (const artifactType of [undefined, ARTIFACT_TYPE]) {
      test(`deletes a hidden referrer with ${
        artifactType ? 'filtered' : 'unfiltered'
      } cached listing`, async ({api, request, cachedQuayConfig}) => {
        const repository = await api.repository(undefined, 'referrerdelete');
        const {username, password} = getTestUsers(cachedQuayConfig).user;
        const token = await getV2Token(
          request,
          API_URL,
          username,
          password,
          `repository:${repository.fullName}:pull,push`,
        );
        const headers = {Authorization: `Bearer ${token}`};
        const url = `${API_URL}/v2/${repository.fullName}`;
        const uncompressedLayer = Buffer.alloc(10240);
        const layer = gzipSync(uncompressedLayer);
        const config = Buffer.from(
          JSON.stringify({
            architecture: 'amd64',
            os: 'linux',
            rootfs: {type: 'layers', diff_ids: [digest(uncompressedLayer)]},
            history: [],
          }),
        );
        for (const blob of [config, layer]) {
          const started = await request.post(`${url}/blobs/uploads/`, {
            headers,
          });
          expect(started.status()).toBe(202);
          const location = new URL(started.headers().location, API_URL);
          expect(location.origin).toBe(new URL(API_URL).origin);
          const uploaded = await request.put(location.toString(), {
            headers: {...headers, 'Content-Type': 'application/octet-stream'},
            params: {digest: digest(blob)},
            data: blob,
          });
          expect(uploaded.status()).toBe(201);
        }
        const image = {
          schemaVersion: 2,
          mediaType: OCI_MANIFEST,
          config: {
            mediaType: 'application/vnd.oci.image.config.v1+json',
            digest: digest(config),
            size: config.length,
          },
          layers: [
            {
              mediaType: 'application/vnd.oci.image.layer.v1.tar+gzip',
              digest: digest(layer),
              size: layer.length,
            },
          ],
        };
        const subject = Buffer.from(JSON.stringify(image));
        const subjectDescriptor = {
          mediaType: OCI_MANIFEST,
          digest: digest(subject),
          size: subject.length,
        };
        const referrer = Buffer.from(
          JSON.stringify({...image, subject: subjectDescriptor, artifactType}),
        );
        const sibling = Buffer.from(
          JSON.stringify({
            ...image,
            subject: subjectDescriptor,
            artifactType,
            annotations: {'quay.test.control': 'retained'},
          }),
        );
        for (const [reference, body] of [
          ['subject', subject],
          [digest(referrer), referrer],
          [digest(sibling), sibling],
        ] as const) {
          const pushed = await request.put(`${url}/manifests/${reference}`, {
            headers: {...headers, 'Content-Type': OCI_MANIFEST},
            data: body,
          });
          expect(pushed.status()).toBe(201);
        }
        const referrersUrl = `${url}/referrers/${subjectDescriptor.digest}`;
        const params = artifactType ? {artifactType} : {};
        const before = await request.get(referrersUrl, {headers, params});
        expect(before.status()).toBe(200);
        expect((await before.json()).manifests).toEqual(
          expect.arrayContaining([
            expect.objectContaining({digest: digest(referrer)}),
            expect.objectContaining({digest: digest(sibling)}),
          ]),
        );
        const referrerUrl = `${url}/manifests/${digest(referrer)}`;
        expect((await request.get(referrerUrl, {headers})).status()).toBe(200);
        expect((await request.delete(referrerUrl, {headers})).status()).toBe(
          202,
        );
        expect((await request.get(referrerUrl, {headers})).status()).toBe(404);
        expect((await request.delete(referrerUrl, {headers})).status()).toBe(
          404,
        );
        for (const retained of [subjectDescriptor.digest, digest(sibling)]) {
          expect(
            (
              await request.get(`${url}/manifests/${retained}`, {headers})
            ).status(),
          ).toBe(200);
        }
        const after = await request.get(referrersUrl, {headers, params});
        expect(after.status()).toBe(200);
        expect((await after.json()).manifests).toEqual([
          expect.objectContaining({digest: digest(sibling)}),
        ]);
      });
    }
  },
);
