import {Tag} from 'src/resources/TagResource';

interface CosignSignatureMap {
  [manifestDigest: string]: {
    signatureTagName: string;
    signatureManifestDigest: string;
  };
}

// Cosign artifact patterns
const COSIGN_SIG_PATTERN = /^sha256-([a-f0-9]{64})\.sig$/;
const COSIGN_SBOM_PATTERN = /^sha256-[a-f0-9]{64}\.sbom$/;
const COSIGN_ATTESTATION_PATTERN = /^sha256-[a-f0-9]{64}\.att$/;

/**
 * Matches cosign style tags and returns the match with a matching group containing the signed manifest digest
 * Cosign tags follow the pattern: sha256-[64 hex characters].sig
 */
function matchCosignSignature(tagName: string): RegExpMatchArray | null {
  return tagName.trim().match(COSIGN_SIG_PATTERN);
}

/**
 * Scans through all tags to find Cosign signature tags and builds a mapping
 * of signed manifest digests to their signature artifacts
 *
 * Note: Only .sig tags are mapped to their signed manifests because these contain
 * the actual cryptographic signatures. SBOM (.sbom) and attestation (.att) tags
 * are related artifacts but don't indicate that a tag is "signed" - they provide
 * additional metadata. We only show the shield icon for tags with actual signatures.
 */
function getCosignSignatures(tags: Tag[]): CosignSignatureMap {
  const cosignedManifests: CosignSignatureMap = {};

  for (const tag of tags) {
    const cosignSignatureMatch = matchCosignSignature(tag.name);

    if (cosignSignatureMatch) {
      const signedManifestDigest = cosignSignatureMatch[1];
      cosignedManifests[`sha256:${signedManifestDigest}`] = {
        signatureTagName: tag.name,
        signatureManifestDigest: tag.manifest_digest,
      };
    }
  }

  return cosignedManifests;
}

/**
 * Detects if a tag name matches Cosign signature patterns or related artifacts
 * Matches: .sig (signatures), .sbom (SBOMs), .att (attestations)
 */
export function isCosignSignatureTag(tagName: string): boolean {
  return (
    COSIGN_SIG_PATTERN.test(tagName) ||
    COSIGN_SBOM_PATTERN.test(tagName) ||
    COSIGN_ATTESTATION_PATTERN.test(tagName)
  );
}

/**
 * Enriches tags with Cosign signature information by adding
 * cosign_signature_tag and cosign_signature_manifest_digest fields
 */
export function enrichTagsWithCosignData(tags: Tag[]): Tag[] {
  const cosignedManifests = getCosignSignatures(tags);

  return tags.map((tag) => {
    if (cosignedManifests[tag.manifest_digest]) {
      return {
        ...tag,
        cosign_signature_tag:
          cosignedManifests[tag.manifest_digest].signatureTagName,
        cosign_signature_manifest_digest:
          cosignedManifests[tag.manifest_digest].signatureManifestDigest,
      };
    }
    return tag;
  });
}
