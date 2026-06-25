import {Tag} from 'src/resources/TagResource';
import {isCosignSignatureTag, enrichTagsWithCosignData} from './cosign';

const digest =
  'sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';

const baseTag: Tag = {
  name: 'latest',
  is_manifest_list: false,
  last_modified: '2024-01-01T00:00:00Z',
  manifest_digest: digest,
  reversion: false,
  size: 1024,
  start_ts: 1704067200,
  manifest_list: {schemaVersion: 2, mediaType: '', manifests: []},
};

function makeTag(overrides: Partial<Tag>): Tag {
  return {...baseTag, ...overrides};
}

describe('isCosignSignatureTag', () => {
  it('detects .sig tags', () => {
    expect(
      isCosignSignatureTag(
        'sha256-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890.sig',
      ),
    ).toBe(true);
  });

  it('detects .sbom tags', () => {
    expect(
      isCosignSignatureTag(
        'sha256-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890.sbom',
      ),
    ).toBe(true);
  });

  it('detects .att tags', () => {
    expect(
      isCosignSignatureTag(
        'sha256-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890.att',
      ),
    ).toBe(true);
  });

  it('rejects regular tags', () => {
    expect(isCosignSignatureTag('latest')).toBe(false);
    expect(isCosignSignatureTag('v1.0.0')).toBe(false);
    expect(isCosignSignatureTag('sha256-short.sig')).toBe(false);
  });

  it('rejects tags with wrong prefix', () => {
    expect(
      isCosignSignatureTag(
        'md5-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890.sig',
      ),
    ).toBe(false);
  });
});

describe('enrichTagsWithCosignData', () => {
  const hexDigest =
    'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
  const signedDigest = `sha256:${hexDigest}`;
  const sigTagName = `sha256-${hexDigest}.sig`;
  const sigManifestDigest =
    'sha256:9999991234567890abcdef1234567890abcdef1234567890abcdef1234567890';

  it('enriches tags whose manifest has a cosign signature', () => {
    const signedTag = makeTag({
      name: 'latest',
      manifest_digest: signedDigest,
    });
    const sigTag = makeTag({
      name: sigTagName,
      manifest_digest: sigManifestDigest,
    });

    const result = enrichTagsWithCosignData([signedTag, sigTag]);

    const enriched = result.find((t) => t.name === 'latest');
    expect(enriched?.cosign_signature_tag).toBe(sigTagName);
    expect(enriched?.cosign_signature_manifest_digest).toBe(sigManifestDigest);
  });

  it('does not enrich tags without signatures', () => {
    const tag = makeTag({name: 'v1.0', manifest_digest: signedDigest});
    const result = enrichTagsWithCosignData([tag]);

    expect(result[0].cosign_signature_tag).toBeUndefined();
    expect(result[0].cosign_signature_manifest_digest).toBeUndefined();
  });

  it('handles empty tag list', () => {
    expect(enrichTagsWithCosignData([])).toEqual([]);
  });

  it('does not mutate original tags', () => {
    const signedTag = makeTag({
      name: 'latest',
      manifest_digest: signedDigest,
    });
    const sigTag = makeTag({
      name: sigTagName,
      manifest_digest: sigManifestDigest,
    });

    enrichTagsWithCosignData([signedTag, sigTag]);
    expect(signedTag.cosign_signature_tag).toBeUndefined();
  });
});
