import {Label} from '@patternfly/react-core';

export default function ManifestDigest(props: ManifestDigestProps) {
  const alg: string = props.digest.split(':')[0];
  const hash: string = props.digest.split(':')[1];
  const condensedHash: string = hash.slice(0, 14);
  return (
    <>
      <Label color="blue" isCompact>
        {alg}
      </Label>
      {condensedHash}
    </>
  );
}

interface ManifestDigestProps {
  digest: string;
}
