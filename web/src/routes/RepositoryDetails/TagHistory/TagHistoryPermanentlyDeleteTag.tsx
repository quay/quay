import {Alert, Button, Label, Modal, Tooltip} from '@patternfly/react-core';
import {TagAction, TagEntry} from './types';
import ManifestDigest from 'src/components/ManifestDigest';
import {useEffect, useState} from 'react';
import {usePermanentlyDeleteTag} from 'src/hooks/UseTags';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {InfoCircleIcon} from '@patternfly/react-icons';

export default function PermanentlyDeleteTag(props: RestoreTagProps) {
  const {tagEntry} = props;
  const {addAlert} = useAlerts();
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const {permanentlyDeleteTag, success, error} = usePermanentlyDeleteTag(
    props.org,
    props.repo,
  );

  let digest: string = null;
  if (tagEntry.action === TagAction.Delete) {
    digest = tagEntry.digest;
  } else if (tagEntry.action === TagAction.Revert) {
    digest = tagEntry.oldDigest;
  }

  useEffect(() => {
    if (success) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Permanently deleted tag ${
          tagEntry.tag.name
        } with manifest ${digest.slice(0, 14)} from time machine`,
      });
      setIsModalOpen(false);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Could not permanently delete tag ${
          tagEntry.tag.name
        } with digest ${digest.slice(0, 14)}`,
      });
      setIsModalOpen(false);
    }
  }, [error]);

  return (
    <>
      <a onClick={() => setIsModalOpen(true)}>
        Delete <Label isCompact>{tagEntry.tag.name}</Label>{' '}
        <ManifestDigest digest={digest} />
      </a>{' '}
      <Tooltip content="The tag deleted cannot be restored within the time machine window and references to the tag will be removed from tag history. Any active tags matching the name and manifest will not be effected.">
        <InfoCircleIcon />
      </Tooltip>
      <Modal
        title="Permanently Delete Tag"
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        variant="medium"
        actions={[
          <Button
            key="modal-action-button"
            variant="primary"
            onClick={() =>
              permanentlyDeleteTag({tag: tagEntry.tag.name, digest: digest})
            }
          >
            Permanently delete tag
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
          title="The tag deleted cannot be restored within the time machine window and references to the tag will be removed from tag history. Any alive tags with the same name and digest will not be effected."
        />
        Are you sure you want to permanently delete tag{' '}
        <Label isCompact>{tagEntry.tag.name}</Label> @{' '}
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
