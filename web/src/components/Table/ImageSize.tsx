import {Skeleton} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {
  getManifestByDigest,
  ManifestByDigestResponse,
} from 'src/resources/TagResource';
import prettyBytes from 'pretty-bytes';
import {useRecoilState} from 'recoil';
import {childManifestSizeState} from 'src/atoms/TagListState';

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

export function ImageSize(props: ImageSizeProps) {
  const {size, loading, err} = useImageSize(
    props.org,
    props.repo,
    props.digest,
  );

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

export function ChildManifestSize(props: ImageSizeProps) {
  const {size, loading, err} = useImageSize(
    props.org,
    props.repo,
    props.digest,
  );

  const [, setChildManifestSize] = useRecoilState(
    childManifestSizeState(props.digest),
  );

  useEffect(() => {
    if (size !== 0) {
      setChildManifestSize(size);
    }
  }, [size]);

  if (loading) {
    return <Skeleton />;
  }
  if (err) {
    return <>Error</>;
  }

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
