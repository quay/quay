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
import {useState} from 'react';
import {IUserResource, updateUser} from 'src/resources/UserResource';
import {getUser, getOrganization} from 'src/resources/AuthResource';

type validate = 'success' | 'error' | 'default';

export function CreateNewUser(props: CreateNewUserProps) {
  const [username, setUsername] = useState(props.user.username);
  const [validatedUsername, setValidatedUsername] =
    useState<validate>('success');
  const [helperText, setHelperText] = useState('');

  const handleModalToggle = () => {
    props.setModalOpen(!props.isModalOpen);
  };

  const handleUsernameChange = async (value: string) => {
    setUsername(value);
    if (!value) {
      setValidatedUsername('error');
      setHelperText('Username cannot be empty');
      return;
    }

    if (value == props.user.username) {
      setHelperText('');
      setValidatedUsername('success');
      return;
    }

    setHelperText('Validating...');
    setValidatedUsername('default');

    // Check username in Existing users
    try {
      const userResponse = await getUser(value);
      if (userResponse.status == 200) {
        setValidatedUsername('error');
        setHelperText('Username already taken');
        return;
      }
    } catch (e) {
      if (e.response.status != 404) {
        setValidatedUsername('error');
        setHelperText('Error validating');
      }
    }

    // Check username in logged-in User's orgs
    try {
      const orgResponse = await getOrganization(value);
      if (orgResponse.status == 200) {
        setValidatedUsername('error');
        setHelperText('Username already taken');
        return;
      }
    } catch (e) {
      if (e.response.status != 404) {
        setValidatedUsername('error');
        setHelperText('Error validating');
      }
    }

    setValidatedUsername('success');
    setHelperText('');
  };

  function fetchDescription() {
    return `The username ${props.user.username} was automatically generated to conform to the Docker CLI guidelines
     for use as a namespace in Quay Container Registry.
     Please confirm the selected username or enter a different username below:`;
  }

  const updateUsername = async () => {
    await updateUser({username: username});
    handleModalToggle();
    window.location.reload();
  };

  return (
    <Modal
      variant={ModalVariant.small}
      title="Confirm Username"
      description={fetchDescription()}
      isOpen={props.isModalOpen}
      onClose={handleModalToggle}
      actions={[
        <Button
          key="create"
          variant="primary"
          isDisabled={validatedUsername != 'success'}
          onClick={() => updateUsername()}
        >
          Confirm Username
        </Button>,
        <Button key="cancel" variant="link" onClick={handleModalToggle}>
          Cancel
        </Button>,
      ]}
    >
      <Form id="confirm-username-form">
        <FormGroup isRequired fieldId="confirm-username-form-group">
          <TextInput
            isRequired
            type="text"
            id="confirm-username-input"
            name="confirm-username-input"
            value={username}
            onChange={(_event, value) => handleUsernameChange(value)}
            validated={validatedUsername}
          />

          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={validatedUsername}
                {...(validatedUsername === 'error' && {
                  icon: <ExclamationCircleIcon />,
                })}
              >
                {helperText}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
      </Form>
    </Modal>
  );
}

type CreateNewUserProps = {
  user: IUserResource;
  isModalOpen: boolean;
  setModalOpen: (boolean) => void;
};
