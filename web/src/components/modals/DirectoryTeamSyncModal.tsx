import {useState} from 'react';
import {
  Alert,
  Button,
  Content,
  TextInput,
  ContentVariants,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';

export default function DirectoryTeamSyncModal(
  props: DirectoryTeamSyncModalProps,
) {
  const [groupName, setGroupName] = useState<string>('');

  const handleInputChange = (value: string) => {
    setGroupName(value.trim());
  };

  return (
    <Modal
      isOpen={props.isModalOpen}
      onClose={props.toggleModal}
      id="directory-sync-modal"
    >
      <ModalHeader title={props.titleText} />
      <ModalBody>
        <Content component={ContentVariants.p}>{props.primaryText}</Content>
        <br />
        <div>
          <Conditional if={props.secondaryText != null}>
            <Content component={ContentVariants.p}>
              {props.secondaryText}
            </Content>
          </Conditional>
          <TextInput
            value={groupName}
            type="text"
            onChange={(_event, value) => handleInputChange(value)}
            id="team-sync-group-name"
          />
        </div>
        <br />
        <Conditional if={props.alertText != null}>
          <Alert isInline variant="warning" title={props.alertText} />
        </Conditional>
      </ModalBody>
      <ModalFooter>
        <Button
          key="confirm"
          variant="primary"
          onClick={() => props.onConfirmSync(groupName)}
          isDisabled={groupName == ''}
        >
          Enable Sync
        </Button>
        <Button key="cancel" variant="link" onClick={props.toggleModal}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}

type DirectoryTeamSyncModalProps = {
  isModalOpen: boolean;
  toggleModal: () => void;
  titleText: string;
  primaryText: string;
  onConfirmSync: (string) => void;
  secondaryText?: React.ReactNode;
  alertText?: string;
};
