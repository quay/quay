import {Skeleton} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {
  getManifestByDigest,
  ManifestByDigestResponse,
} from 'src/resources/TagResource';
import prettyBytes from 'pretty-bytes';

export default function ImageSize(props: ImageSizeProps) {
  const [size, setSize] = useState<number>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [err, setErr] = useState<boolean>(false);

  useEffect(() => {
    (async () => {
      try {
        const manifestResp: ManifestByDigestResponse =
          await getManifestByDigest(props.org, props.repo, props.digest);
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
  }, [props.digest]);

  if (loading) {
    return <Skeleton />;
  }
  if (err) {
    return <>Error</>;
  }

  // Behavior based on old UI
  if (size === 0) {
    return <>Unknown</>;
  }

  return <>{prettyBytes(size)}</>;
}

interface ImageSizeProps {
  org: string;
  repo: string;
  digest: string;
  // TODO: Add in option to provide an already existing manifest,
  //   remove the need to make the call again.
  // manifest?: Manifest;
}
