import {Skeleton} from '@patternfly/react-core';
import prettyBytes from 'pretty-bytes';
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

export function ChildManifestSize(props: ChildManifestSizeProps) {
  // Use size directly from manifest data (already fetched in parent)
  const size = props.manifest?.size || 0;

  if (size === 0) {
    return <>Unknown</>;
  }

  return <>{prettyBytes(size)}</>;
}

interface ImageSizeProps {
  org: string;
  repo: string;
  digest: string;
}

interface ChildManifestSizeProps {
  manifest: {
    size: number;
    digest: string;
  };
}
