import {useEffect, useState} from 'react';
import {
  getManifestByDigest,
  ManifestByDigestResponse,
} from 'src/resources/TagResource';

export function useImageSize(org: string, repo: string, digest: string) {
  const [size, setSize] = useState<number>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<boolean>(false);

  useEffect(() => {
    (async () => {
      try {
        const manifestResp: ManifestByDigestResponse =
          await getManifestByDigest(org, repo, digest);
        const calculatedSizeMesnifestResp = manifestResp.layers
          ? manifestResp.layers.reduce(
              (prev, curr) => prev + curr.compressed_size,
              0,
            )
          : 0;
        setSize(calculatedSizeMesnifestResp);
      } catch (err) {
        setErr(true);
      } finally {
        setLoading(false);
      }
    })();
  }, [digest]);

  return {size, loading, err};
}
