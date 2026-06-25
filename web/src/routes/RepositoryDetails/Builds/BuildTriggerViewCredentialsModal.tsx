import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
} from '@patternfly/react-core';
import {RepositoryBuildTrigger} from 'src/resources/BuildResource';
import ViewCredentials from './BuilTriggerViewCredentials';

export default function BuildTriggerViewCredentialsModal(
  props: BuildTriggerViewCredentialsModalProps,
) {
  return (
    <Modal
      id="build-trigger-view-credentials-modal"
      isOpen={props.isOpen}
      onClose={() => props.onClose()}
      variant={ModalVariant.medium}
      style={{
        overflowX: 'visible',
        overflowY: 'visible',
      }}
    >
      <ModalHeader title="Trigger Credentials" />
      <ModalBody>
        <ViewCredentials trigger={props.trigger} />
      </ModalBody>
      <ModalFooter>
        <Button key="cancel" variant="primary" onClick={() => props.onClose()}>
          Done
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface BuildTriggerViewCredentialsModalProps {
  trigger: RepositoryBuildTrigger;
  isOpen: boolean;
  onClose: () => void;
}
