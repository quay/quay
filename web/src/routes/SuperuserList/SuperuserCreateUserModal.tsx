import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  FormHelperText,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import ExclamationCircleIcon from '@patternfly/react-icons/dist/esm/icons/exclamation-circle-icon';
import {isValidEmail} from 'src/libs/utils';
import {useState} from 'react';
import FormError from 'src/components/errors/FormError';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {Validation} from '../OrganizationsList/CreateOrganizationModal';
import {useCreateUser} from 'src/hooks/UseSuperuserUsers';

const defaultMessage: Validation = {
  message:
    'Name of the user. Must be all lowercase, at least 4 characters long and at most 30 characters long',
  isValid: true,
  type: 'default',
};

export const SuperuserCreateUserModal = (
  props: SuperuserCreateUserModalProps,
): JSX.Element => {
  const [newUsername, setNewUsername] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [invalidEmailFlag, setInvalidEmailFlag] = useState(false);
  const [validation, setValidation] = useState<Validation>(defaultMessage);
  const [err, setErr] = useState<string>();

  const {createUser} = useCreateUser({
    onSuccess: () => props.handleModalToggle(),
    onError: (err) => {
      setErr(addDisplayError('Unable to create user', err));
    },
  });

  const handleNameInputChange = (value: string) => {
    const regex = /^[a-z0-9_]{4,30}$/;
    if (!regex.test(value) || value.length >= 30 || value.length < 4) {
      setValidation({
        message:
          'Username can only consist of either lowercase letters(a-z), digits(0-9), or underscore(_). It must be at least 4 characters and at most 30 characters long',
        isValid: false,
        type: 'error',
      });
    } else {
      setValidation(defaultMessage);
    }
    setNewUsername(value);
  };

  const handleEmailInputChange = (value: string) => {
    setNewUserEmail(value);

    // Check if the new email value is not empty
    if (value.length !== 0) {
      // Validate the email format using isValidEmail function
      isValidEmail(value) ? setInvalidEmailFlag(false) : setInvalidEmailFlag(true);
    } else {
      // If the value is empty, consider it invalid (optional step based on your requirements)
      setInvalidEmailFlag(true);
    }
  };

  const createUserHandler = async () => {
    await createUser(newUsername, newUserEmail);
  };

  const onInputBlur = () => {
    if (newUserEmail.length !== 0) {
      isValidEmail(newUserEmail)
        ? setInvalidEmailFlag(false)
        : setInvalidEmailFlag(true);
    } else {
      return;
    }
  };

  return (
    <Modal
      title="Create User"
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          id="create-user-confirm"
          key="confirm"
          variant="primary"
          onClick={createUserHandler}
          form="modal-with-form-form"
          isDisabled={invalidEmailFlag || !newUsername || !newUserEmail || !validation.isValid}
        >
          Create
        </Button>,
        <Button
          id="create-user-cancel"
          key="cancel"
          variant="link"
          onClick={props.handleModalToggle}
        >
          Cancel
        </Button>,
      ]}
    >
      <FormError message={err} setErr={setErr} />
      <Form id="create-user-modal" isWidthLimited>
        <FormGroup
          isInline
          label="Username"
          isRequired
          fieldId="create-user-name"
        >
          <TextInput
            isRequired
            type="text"
            id="create-user-name-input"
            value={newUsername}
            onChange={(_event, value) => handleNameInputChange(value)}
            validated={validation.type}
          />

          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={validation.type}
                {...(validation.type === 'error' && {
                  icon: <ExclamationCircleIcon />,
                })}
              >
                {validation.message}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <FormGroup label="User Email" fieldId="create-user-email" isRequired>
          <TextInput
            isRequired
            type="email"
            id="create-user-email-input"
            name="create-user-email-input"
            value={newUserEmail}
            onChange={(_event, value) => handleEmailInputChange(value)}
            validated={invalidEmailFlag ? 'error' : 'default'}
          />

          <FormHelperText>
            <HelperText>
              {invalidEmailFlag ? (
                <HelperTextItem
                  variant="error"
                  icon={<ExclamationCircleIcon />}
                >
                  Invalid email format, it should be of the form email@provider.com
                </HelperTextItem>
              ) : (
                <HelperTextItem>{'This must be a valid email address'}</HelperTextItem>
              )}
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <br />
      </Form>
    </Modal>
  );
};

type SuperuserCreateUserModalProps = {
  isModalOpen: boolean;
  handleModalToggle?: () => void;
};
