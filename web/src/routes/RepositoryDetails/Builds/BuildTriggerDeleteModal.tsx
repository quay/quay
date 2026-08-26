import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
} from '@patternfly/react-core';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useDeleteBuildTrigger} from 'src/hooks/UseBuildTriggers';

export default function BuildTriggerDeleteModal(
  props: BuildTriggerDeleteModalProps,
) {
  const {addAlert} = useUI();
  const {deleteTrigger} = useDeleteBuildTrigger(
    props.org,
    props.repo,
    props.trigger_uuid,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Successfully deleted trigger',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: 'Failed to delete trigger',
        });
      },
    },
  );

  return (
    <Modal
      id="build-trigger-delete-modal"
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      <ModalHeader title="Delete Build Trigger" />
      <ModalBody>
        Are you sure you want to delete this build trigger? No further builds
        will be automatically started.
      </ModalBody>
      <ModalFooter>
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Done
        </Button>
        <Button
          key="modal-action-button"
          variant="primary"
          onClick={() => {
            deleteTrigger();
            props.onClose();
          }}
        >
          Delete Trigger
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface BuildTriggerDeleteModalProps {
  org: string;
  repo: string;
  trigger_uuid: string;
  isOpen: boolean;
  onClose: () => void;
}
