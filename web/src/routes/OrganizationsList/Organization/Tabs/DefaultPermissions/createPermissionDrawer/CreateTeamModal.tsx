import {
  Button,
  Form,
  FormGroup,
  Modal,
  ModalVariant,
  TextInput,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useCreateTeam} from 'src/hooks/UseTeams';

type validate = 'success' | 'error' | 'default';

export const CreateTeamModal = (props: CreateTeamModalProps): JSX.Element => {
  const [inputTeamName, setInputTeamName] = useState('');
  const [inputTeamDescription, setInputTeamDescription] = useState('');

  const [validatedName, setValidatedName] = useState<validate>('default');
  const [nameHelperText, setNameHelperText] = useState(props.nameHelperText);
  const {addAlert} = useAlerts();

  const handleNameChange = (name: string) => {
    setInputTeamName(name);
    props.setTeamName(name);
    setNameHelperText('Validating...');
  };

  const handleDescriptionChange = (descr: string) => {
    setInputTeamDescription(descr);
    props.setDescription(descr);
  };

  useEffect(() => {
    if (inputTeamName === '') {
      return;
    }
    props.validateName(inputTeamName)
      ? setValidatedName('success')
      : setValidatedName('error');

    setNameHelperText(props.nameHelperText);
  }, [inputTeamName]);

  const {createNewTeamHook} = useCreateTeam(props.orgName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created new team: ${inputTeamName}`,
      });
      props.setAppliedTo({
        is_robot: false,
        name: props.teamName,
        kind: 'team',
      });
      if (props?.handleWizardToggle) {
        props?.handleWizardToggle();
      }
      props.handleModalToggle();
    },
    onError: () => {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to create new team',
      });
    },
  });

  const onCreateTeam = () => {
    createNewTeamHook({
      teamName: inputTeamName,
      description: inputTeamDescription,
    });
  };

  return (
    <Modal
      title="Create team"
      variant={ModalVariant.medium}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          data-testid="create-team-confirm"
          id="create-team-confirm"
          key="Proceed"
          variant="primary"
          onClick={onCreateTeam}
          form="modal-with-form-form"
          isDisabled={validatedName !== 'success'}
        >
          Proceed
        </Button>,
        <Button
          id="create-team-cancel"
          key="cancel"
          variant="link"
          onClick={props.handleModalToggle}
        >
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <FormGroup
          label={props.nameLabel}
          fieldId="form-name"
          isRequired
          helperText={nameHelperText}
          helperTextInvalid={nameHelperText}
          validated={validatedName}
          helperTextInvalidIcon={<ExclamationCircleIcon />}
        >
          <TextInput
            data-testid="new-team-name-input"
            isRequired
            type="text"
            id="team-modal-form-name"
            name="form-name"
            value={inputTeamName}
            onChange={handleNameChange}
            validated={validatedName}
          />
        </FormGroup>
        <FormGroup
          label={props.descriptionLabel}
          fieldId="form-description"
          helperText={props.helperText}
        >
          <TextInput
            data-testid="new-team-description-input"
            type="text"
            id="team-modal-form-description"
            name="form-description"
            value={inputTeamDescription}
            onChange={handleDescriptionChange}
          />
        </FormGroup>
      </Form>
    </Modal>
  );
};

interface CreateTeamModalProps {
  teamName: string;
  setTeamName: (teamName: string) => void;
  description: string;
  setDescription: (descr: string) => void;
  orgName: string;
  nameLabel: string;
  descriptionLabel: string;
  helperText: string;
  nameHelperText: string;
  validateName: (string) => boolean;
  isModalOpen: boolean;
  handleModalToggle: () => void;
  handleWizardToggle?: () => void;
  setAppliedTo: (string) => void;
}
