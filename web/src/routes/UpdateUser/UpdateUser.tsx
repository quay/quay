import React, {useState, useEffect} from 'react';
import {
  Button,
  Form,
  FormGroup,
  TextInput,
  Title,
  Spinner,
  Card,
  CardBody,
} from '@patternfly/react-core';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  BanIcon,
} from '@patternfly/react-icons';
import {useNavigate} from 'react-router-dom';
import {useCurrentUser, useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useUsernameValidation} from 'src/hooks/UseUsernameValidation';
import {UpdateUserRequest} from 'src/resources/UserResource';

function isValidUsername(username: string): boolean {
  if (!username || username.length < 2) {
    return false;
  }
  return /^(?=.{2,255}$)([a-z0-9]+(?:[._-][a-z0-9]+)*)$/i.test(username);
}

export default function UpdateUser() {
  const navigate = useNavigate();
  const {user, loading: userLoading} = useCurrentUser();
  const [isUpdating, setIsUpdating] = useState(false);
  const [username, setUsername] = useState('');
  const [metadata, setMetadata] = useState({
    given_name: '',
    family_name: '',
    company: '',
    location: '',
  });

  const {state: usernameState, validateUsername} = useUsernameValidation(
    user?.username,
  );

  const {updateUser} = useUpdateUser({
    onSuccess: (updatedUser) => {
      if (updatedUser?.prompts?.length) {
        setIsUpdating(false);
      } else {
        navigate('/');
      }
    },
    onError: () => setIsUpdating(false),
  });

  useEffect(() => {
    if (!userLoading && user) {
      if (user.anonymous) {
        navigate('/signin');
        return;
      }

      if (!user.prompts || user.prompts.length === 0) {
        navigate('/');
        return;
      }

      const initialUsername = user.username || '';
      setUsername(initialUsername);

      // Validate pre-filled username
      if (initialUsername) {
        validateUsername(initialUsername);
      }
    }
  }, [user, userLoading, navigate]);

  const hasPrompt = (promptName: string) => {
    return user?.prompts?.includes(promptName) || false;
  };

  const handleUsernameChange = (value: string) => {
    setUsername(value);
    validateUsername(value);
  };

  const handleUpdateUser = async (data: Partial<UpdateUserRequest>) => {
    setIsUpdating(true);
    await updateUser(data);
  };

  const getValidationIcon = () => {
    switch (usernameState) {
      case 'confirmed':
        return (
          <CheckCircleIcon
            style={{color: 'var(--pf-v5-global--success-color--100)'}}
          />
        );
      case 'existing':
        return (
          <BanIcon style={{color: 'var(--pf-v5-global--danger-color--100)'}} />
        );
      case 'error':
        return (
          <ExclamationTriangleIcon
            style={{color: 'var(--pf-v5-global--warning-color--100)'}}
          />
        );
      case 'confirming':
        return <Spinner size="sm" />;
      default:
        return null;
    }
  };

  const getValidationMessage = () => {
    switch (usernameState) {
      case 'confirmed':
        return 'Username valid';
      case 'existing':
        return 'Username already taken';
      case 'error':
        return 'Could not check username';
      case 'editing':
        return !isValidUsername(username)
          ? 'Usernames must be alphanumeric and be at least two characters in length'
          : '';
      default:
        return '';
    }
  };

  if (userLoading || !user) {
    return <Spinner size="lg" />;
  }

  return (
    <div style={{maxWidth: '600px', margin: '2rem auto', padding: '0 1rem'}}>
      {/* Username Confirmation */}
      {hasPrompt('confirm_username') && !isUpdating && (
        <Card>
          <CardBody>
            <Title headingLevel="h2">Confirm Username</Title>
            <p>
              The username <strong>{user.username}</strong> was automatically
              generated to conform to the Docker CLI guidelines for use as a
              namespace in Red Hat Quay.
            </p>
            <p>
              Please confirm the selected username or enter a different username
              below:
            </p>

            <Form
              onSubmit={(e) => {
                e.preventDefault();
                handleUpdateUser({username});
              }}
            >
              <FormGroup label="Username" fieldId="username">
                <TextInput
                  id="username"
                  value={username}
                  onChange={(_event, value) => handleUsernameChange(value)}
                  validated={
                    usernameState === 'existing' ||
                    (usernameState === 'editing' && !isValidUsername(username))
                      ? 'error'
                      : 'default'
                  }
                />

                <div
                  style={{
                    marginTop: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  {getValidationIcon()}
                  <span
                    style={{
                      fontSize: '0.875rem',
                      color:
                        usernameState === 'existing' ||
                        usernameState === 'error'
                          ? 'var(--pf-v5-global--danger-color--100)'
                          : 'var(--pf-v5-global--color--100)',
                    }}
                  >
                    {getValidationMessage()}
                  </span>
                </div>
              </FormGroup>

              <Button
                type="submit"
                variant="primary"
                isDisabled={
                  usernameState === 'existing' ||
                  usernameState === 'error' ||
                  !isValidUsername(username)
                }
                isLoading={isUpdating}
              >
                Confirm Username
              </Button>
            </Form>
          </CardBody>
        </Card>
      )}

      {/* Profile Metadata */}
      {!hasPrompt('confirm_username') &&
        (hasPrompt('enter_name') || hasPrompt('enter_company')) &&
        !isUpdating && (
          <Card>
            <CardBody>
              <Title headingLevel="h2">Tell us a bit more about yourself</Title>
              <p>This information will be displayed in your user profile.</p>

              <Form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleUpdateUser(metadata);
                }}
                style={{marginTop: '1.5rem'}}
              >
                <FormGroup label="Given Name" fieldId="given-name">
                  <TextInput
                    id="given-name"
                    placeholder="Given Name"
                    value={metadata.given_name}
                    onChange={(_event, value) =>
                      setMetadata({...metadata, given_name: value})
                    }
                  />
                </FormGroup>

                <FormGroup label="Family Name" fieldId="family-name">
                  <TextInput
                    id="family-name"
                    placeholder="Family Name"
                    value={metadata.family_name}
                    onChange={(_event, value) =>
                      setMetadata({...metadata, family_name: value})
                    }
                  />
                </FormGroup>

                <FormGroup label="Company" fieldId="company">
                  <TextInput
                    id="company"
                    placeholder="Company name"
                    value={metadata.company}
                    onChange={(_event, value) =>
                      setMetadata({...metadata, company: value})
                    }
                  />
                </FormGroup>

                <FormGroup label="Location" fieldId="location">
                  <TextInput
                    id="location"
                    placeholder="Location"
                    value={metadata.location}
                    onChange={(_event, value) =>
                      setMetadata({...metadata, location: value})
                    }
                  />
                </FormGroup>

                <div
                  style={{marginTop: '1.5rem', display: 'flex', gap: '1rem'}}
                >
                  <Button
                    type="submit"
                    variant="primary"
                    isDisabled={
                      !metadata.given_name &&
                      !metadata.family_name &&
                      !metadata.company
                    }
                    isLoading={isUpdating}
                  >
                    Save Details
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      handleUpdateUser({
                        company: '',
                        given_name: '',
                        family_name: '',
                        location: '',
                      })
                    }
                    isDisabled={isUpdating}
                  >
                    No thanks
                  </Button>
                </div>
              </Form>
            </CardBody>
          </Card>
        )}
    </div>
  );
}
