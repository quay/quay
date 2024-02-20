import {useState} from 'react';
import {
  Alert,
  Button,
  HelperText,
  HelperTextItem,
  Modal,
  Text,
  TextInput,
  TextVariants,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import ExclamationCircleIcon from '@patternfly/react-icons/dist/esm/icons/exclamation-circle-icon';

interface Validation {
  message: string;
  isValid: boolean;
  type: 'default' | 'error';
}

const defaultMessage: Validation = {
  message:
    'The expected OIDC group name format is - org_name:team_name. Must match ^[a-z0-9][a-z0-9]+:[a-z0-9]+$',
  isValid: false,
  type: 'default',
};

export default function OIDCTeamSyncModal(props: OIDCTeamSyncModalProps) {
  const [groupName, setGroupName] = useState<string>('');
  const [validation, setValidation] = useState<Validation>(defaultMessage);

  const handleInputChange = (value: string) => {
    const regex = /^[a-z0-9][a-z0-9]+:[a-z0-9]+$/;
    if (!regex.test(value)) {
      setValidation({
        message:
          'The expected OIDC group name format is - org_name:team_name. Must match ^[a-z0-9][a-z0-9]+:[a-z0-9]+$',
        isValid: false,
        type: 'error',
      });
    } else {
      defaultMessage['isValid'] = true;
      setValidation(defaultMessage);
    }
    setGroupName(value);
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
          isDisabled={!validation.isValid}
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
          validated={validation.type}
        />
        <HelperText id="oidc-team-sync-helper-text">
          <HelperTextItem
            variant={validation.type}
            {...(validation.type === 'error' && {
              icon: <ExclamationCircleIcon />,
            })}
          >
            {validation.message}
          </HelperTextItem>
        </HelperText>
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
