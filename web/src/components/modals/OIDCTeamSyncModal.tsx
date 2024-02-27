import {useState} from 'react';
import {
  Alert,
  Button,
  Modal,
  Text,
  TextInput,
  TextVariants,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';

export default function OIDCTeamSyncModal(props: OIDCTeamSyncModalProps) {
  const [groupName, setGroupName] = useState<string>('');

  const handleInputChange = (value: string) => {
    setGroupName(value.trim());
  };

  return (
    <Modal
      width="50%"
      title={props.titleText}
      isOpen={props.isModalOpen}
      onClose={props.toggleModal}
      id="directory-sync-modal"
      actions={[
        <Button
          key="confirm"
          variant="primary"
          onClick={() => props.onConfirmSync(groupName)}
          isDisabled={groupName == ''}
        >
          Enable Sync
        </Button>,
        <Button key="cancel" variant="link" onClick={props.toggleModal}>
          Cancel
        </Button>,
      ]}
    >
      <Text component={TextVariants.p}>{props.primaryText}</Text>
      <br />
      <div>
        <Conditional if={props.secondaryText != null}>
          <Text component={TextVariants.p}>{props.secondaryText}</Text>
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
    </Modal>
  );
}

type OIDCTeamSyncModalProps = {
  isModalOpen: boolean;
  toggleModal: () => void;
  titleText: string;
  primaryText: string;
  onConfirmSync: (string) => void;
  secondaryText?: string;
  alertText?: string;
};
