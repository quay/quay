import ManifestDigest from 'src/components/ManifestDigest';
import {TagAction, TagEntry} from './types';
import {ReactElement, useEffect, useState} from 'react';
import {Alert, Button, Label, Modal} from '@patternfly/react-core';
import {useRestoreTag} from 'src/hooks/UseTags';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

export default function RestoreTag(props: RestoreTagProps) {
  const {tagEntry, org, repo} = props;
  const {addAlert} = useAlerts();
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const {restoreTag, success, error} = useRestoreTag(org, repo);

  if (
    ![TagAction.Delete, TagAction.Move, TagAction.Revert].includes(
      tagEntry.action,
    )
  ) {
    return null;
  }

  let digest: string = null;
  let message: ReactElement = null;
  switch (tagEntry.action) {
    case TagAction.Delete:
      digest = tagEntry.digest;
      message = (
        <>
          Restore to <ManifestDigest digest={tagEntry.digest} />
        </>
      );
      break;
    case TagAction.Move:
      digest = tagEntry.oldDigest;
      message = (
        <>
          Revert to <ManifestDigest digest={tagEntry.oldDigest} />
        </>
      );
      break;
    case TagAction.Revert:
      digest = tagEntry.oldDigest;
      message = (
        <>
          Restore to <ManifestDigest digest={tagEntry.oldDigest} />
        </>
      );
      break;
  }

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Restored tag ${tagEntry.tag.name} to digest ${digest.slice(
          0,
          14,
        )} successfully`,
      });
      setIsModalOpen(false);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Could not restore tag ${
          tagEntry.tag.name
        } to digest ${digest.slice(0, 14)}`,
      });
      setIsModalOpen(false);
    }
  }, [error]);

  return (
    <>
      <a onClick={() => setIsModalOpen(true)}>{message}</a>
      <Modal
        title="Restore Tag"
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        variant="medium"
        actions={[
          <Button
            key="modal-action-button"
            variant="primary"
            onClick={() => restoreTag({tag: tagEntry.tag.name, digest: digest})}
          >
            Restore tag
          </Button>,
          <Button
            key="cancel"
            variant="secondary"
            onClick={() => setIsModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        <Alert
          isInline
          variant="warning"
          title="This will change the image to which the tag points."
        />
        Are you sure you want to restore tag{' '}
        <Label isCompact>{tagEntry.tag.name}</Label> to image{' '}
        <ManifestDigest digest={digest} />?
      </Modal>
    </>
  );
}

interface RestoreTagProps {
  org: string;
  repo: string;
  tagEntry: TagEntry;
}
