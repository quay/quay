import {Button, Modal, ModalVariant} from '@patternfly/react-core';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useToggleBuildTrigger} from 'src/hooks/UseBuildTriggers';

export default function BuildTriggerToggleModal(
  props: BuildTriggerToggleModalProps,
) {
  const {addAlert} = useAlerts();
  const {toggleTrigger} = useToggleBuildTrigger(
    props.org,
    props.repo,
    props.trigger_uuid,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: `Successfully ${
            props.enabled ? 'disabled' : 'enabled'
          } trigger`,
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: `Failed to ${props.enabled ? 'disabled' : 'enabled'} trigger`,
        });
      },
    },
  );
  const title = props.enabled
    ? 'Disable Build Trigger'
    : 'Enable Build Trigger';

  return (
    <Modal
      id="build-trigger-toggle-modal"
      title={title}
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      actions={[
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Cancel
        </Button>,
        <Button
          key="modal-action-button"
          variant="primary"
          onClick={() => {
            toggleTrigger(!props.enabled);
            props.onClose();
          }}
        >
          {title}
        </Button>,
      ]}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      Are you sure you want to {props.enabled ? 'disable' : 'enable'} this build
      trigger?
    </Modal>
  );
}

interface BuildTriggerToggleModalProps {
  org: string;
  repo: string;
  trigger_uuid: string;
  enabled: boolean;
  isOpen: boolean;
  onClose: () => void;
}
