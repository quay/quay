import {Button, Modal, ModalVariant} from '@patternfly/react-core';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';
import ViewCredentials from './BuilTriggerViewCredentials';

export default function BuildTriggerViewCredentialsModal(
  props: BuildTriggerViewCredentialsModalProps,
) {
  return (
    <Modal
      id="build-trigger-view-credentials-modal"
      title="Trigger Credentials"
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      actions={[
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Done
        </Button>,
      ]}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      <ViewCredentials trigger={props.trigger} />
    </Modal>
  );
}

interface BuildTriggerViewCredentialsModalProps {
  trigger: RepositoryBuildTrigger;
  isOpen: boolean;
  onClose: () => void;
}
