import {Label} from '@patternfly/react-core';
import {TagAction, TagEntry} from './types';
import ManifestDigest from 'src/components/ManifestDigest';

export default function TagActionDescription({tagEntry}: {tagEntry: TagEntry}) {
  switch (tagEntry.action) {
    case TagAction.Create:
      return (
        <>
          <Label isCompact>{tagEntry.tag.name}</Label> was created pointing to{' '}
          <ManifestDigest digest={tagEntry.digest} />
        </>
      );
    case TagAction.Recreate:
      return (
        <>
          <Label isCompact>{tagEntry.tag.name}</Label> was recreated pointing to{' '}
          <ManifestDigest digest={tagEntry.digest} />
        </>
      );
    case TagAction.Delete:
      return (
        <>
          <Label isCompact>{tagEntry.tag.name}</Label>{' '}
          {tagEntry.time >= new Date().getTime()
            ? `will expire`
            : `was deleted`}
        </>
      );
    case TagAction.Revert:
      return (
        <>
          <Label isCompact>{tagEntry.tag.name}</Label> was reverted to{' '}
          <ManifestDigest digest={tagEntry.digest} /> from{' '}
          <ManifestDigest digest={tagEntry.oldDigest} />
        </>
      );
    case TagAction.Move:
      return (
        <>
          <Label isCompact>{tagEntry.tag.name}</Label> was moved to{' '}
          <ManifestDigest digest={tagEntry.digest} /> from{' '}
          <ManifestDigest digest={tagEntry.oldDigest} />
        </>
      );
  }
}
