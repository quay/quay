import prettyBytes from 'pretty-bytes';
import {Manifest} from 'src/resources/TagResource';

export default function ManifestListSize(props: ManifestListSizeProps) {
  // Use sizes directly from manifest data (already fetched in parent)
  const sizes = props.manifests
    .map((manifest) => manifest.size)
    .filter((size) => size > 0);

  // If no valid sizes, show Unknown
  if (sizes.length === 0) {
    return <>Unknown</>;
  }

  // Single manifest or all same size
  if (sizes.length === 1) {
    return <>{prettyBytes(sizes[0])}</>;
  }

  // Multiple manifests with different sizes - show range
  const lowestValue = Math.min(...sizes);
  const highestValue = Math.max(...sizes);

  return (
    <>
      {prettyBytes(lowestValue)} ~ {prettyBytes(highestValue)}
    </>
  );
}

interface ManifestListSizeProps {
  manifests: Manifest[];
}
