import {Skeleton} from '@patternfly/react-core';
import prettyBytes from 'pretty-bytes';
import {Manifest} from 'src/resources/TagResource';
import {useRecoilValue} from 'recoil';
import {childManifestSizeState} from 'src/atoms/TagListState';

export default function ManifestListSize(props: ManifestListSizeProps) {
  const childManifestSizes = props.manifests.map((manifest) =>
    useRecoilValue(childManifestSizeState(manifest.digest)),
  );

  const loadedSizes = childManifestSizes
    .filter((size) => size != null)
    .map((size) => size);

  const loading = loadedSizes.length < props.manifests.length;

  if (loading) {
    return <Skeleton />;
  } else {
    if (loadedSizes.length === 1) {
      return <>{prettyBytes(loadedSizes[0])}</>;
    } else {
      const lowestValue = Math.min(...loadedSizes);
      const highestValue = Math.max(...loadedSizes);

      return (
        <>
          {prettyBytes(lowestValue)} ~ {prettyBytes(highestValue)}
        </>
      );
    }
  }
}

interface ManifestListSizeProps {
  manifests: Manifest[];
}
