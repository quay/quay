import {Skeleton} from '@patternfly/react-core';
import prettyBytes from 'pretty-bytes';
import {useEffect} from 'react';
import {useSetRecoilState} from 'recoil';
import {childManifestSizeState} from 'src/atoms/TagListState';
import {useImageSize} from 'src/hooks/UseImageSize';

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

  const setChildManifestSize = useSetRecoilState(
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
