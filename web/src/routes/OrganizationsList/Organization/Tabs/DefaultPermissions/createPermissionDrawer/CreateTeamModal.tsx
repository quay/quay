import {
  Button,
  Form,
  FormGroup,
  Modal,
  ModalVariant,
  TextInput,
  FormHelperText,
  HelperText,
  HelperTextItem,
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

  const handleNameChange = (
    _event: React.FormEvent<HTMLInputElement>,
    name: string,
  ) => {
    setInputTeamName(name);
    props.setTeamName(name);
    setNameHelperText('Validating...');
  };

  const handleDescriptionChange = (
    _event: React.FormEvent<HTMLInputElement>,
    descr: string,
  ) => {
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
      if (props?.setAppliedTo) {
        props.setAppliedTo({
          is_robot: false,
          name: props.teamName,
          kind: 'team',
        });
      }
      props.handleModalToggle();
      if (props?.handleWizardToggle) {
        props?.handleWizardToggle();
      }
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
        <FormGroup label={props.nameLabel} fieldId="form-name" isRequired>
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

          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={validatedName}
                {...(validatedName === 'error' && {
                  icon: <ExclamationCircleIcon />,
                })}
              >
                {nameHelperText}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <FormGroup label={props.descriptionLabel} fieldId="form-description">
          <TextInput
            data-testid="new-team-description-input"
            type="text"
            id="team-modal-form-description"
            name="form-description"
            value={inputTeamDescription}
            onChange={handleDescriptionChange}
          />

          <FormHelperText>
            <HelperText>
              <HelperTextItem>{props.helperText}</HelperTextItem>
            </HelperText>
          </FormHelperText>
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
  setAppliedTo?: (string) => void;
}
