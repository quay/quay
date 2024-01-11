import {Button, Modal, ModalVariant} from '@patternfly/react-core';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useDeleteBuildTrigger} from 'src/hooks/UseBuildTriggers';

export default function BuildTriggerDeleteModal(
  props: BuildTriggerDeleteModalProps,
) {
  const {addAlert} = useAlerts();
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
      title="Delete Build Trigger"
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      actions={[
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Done
        </Button>,
        <Button
          key="modal-action-button"
          variant="primary"
          onClick={() => {
            deleteTrigger();
            props.onClose();
          }}
        >
          Delete Trigger
        </Button>,
      ]}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      Are you sure you want to delete this build trigger? No further builds will
      be automatically started.
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
