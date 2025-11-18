import {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  Button,
  Alert,
  ClipboardCopy,
} from '@patternfly/react-core';
import {useForm} from 'react-hook-form';
import {useCreateUser} from 'src/hooks/UseCreateUser';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {isFreshLoginError} from 'src/utils/freshLoginErrors';

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface CreateUserFormData {
  username: string;
  email: string;
}

export function CreateUserModal(props: CreateUserModalProps) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(
    null,
  );
  const {addAlert} = useUI();

  const {
    register,
    handleSubmit,
    formState: {errors, isValid},
    reset,
  } = useForm<CreateUserFormData>({
    mode: 'onChange',
    defaultValues: {
      username: '',
      email: '',
    },
  });

  const {createUser, isLoading} = useCreateUser({
    onSuccess: (username: string, password: string) => {
      setGeneratedPassword(password);
      setErrorMessage(null);
      // Don't close modal or call onSuccess yet - show password first
    },
    onError: (err: any) => {
      const errorMsg =
        err?.response?.data?.error_message ||
        err?.response?.data?.message ||
        err?.message ||
        'Failed to create user';
      // Filter out fresh login errors to prevent duplicate alerts
      if (isFreshLoginError(errorMsg)) {
        return;
      }
      setErrorMessage(errorMsg);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to create user',
        message: errorMsg,
      });
    },
  });

  const onSubmit = (data: CreateUserFormData) => {
    setErrorMessage(null);
    createUser({
      username: data.username,
      email: data.email,
    });
  };

  const handleClose = () => {
    // Check if user was created successfully BEFORE clearing state
    if (generatedPassword) {
      props.onSuccess();
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created user`,
      });
    }

    // Then clear state and close
    reset();
    setErrorMessage(null);
    setGeneratedPassword(null);
    props.onClose();
  };

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Create New User"
      isOpen={props.isOpen}
      onClose={handleClose}
      data-testid="create-user-modal"
      actions={
        generatedPassword
          ? [
              <Button
                key="close"
                variant="primary"
                onClick={handleClose}
                data-testid="create-user-done"
              >
                Done
              </Button>,
            ]
          : [
              <Button
                key="submit"
                type="submit"
                variant="primary"
                isDisabled={!isValid || isLoading}
                isLoading={isLoading}
                onClick={handleSubmit(onSubmit)}
                data-testid="create-user-submit"
              >
                Create User
              </Button>,
              <Button
                key="cancel"
                variant="link"
                onClick={handleClose}
                data-testid="create-user-cancel"
              >
                Cancel
              </Button>,
            ]
      }
    >
      {generatedPassword ? (
        <>
          <Alert
            variant="success"
            title="User created successfully"
            isInline
            style={{marginBottom: '1em'}}
          >
            The user has been created with a temporary password. Please provide
            this password to the user securely.
          </Alert>
          <FormGroup
            label="Temporary Password"
            fieldId="generated-password"
            helperText="This password will only be displayed once. Make sure to copy it before closing."
          >
            <ClipboardCopy
              isReadOnly
              hoverTip="Copy"
              clickTip="Copied"
              data-testid="generated-password-copy"
            >
              {generatedPassword}
            </ClipboardCopy>
          </FormGroup>
        </>
      ) : (
        <Form onSubmit={handleSubmit(onSubmit)}>
          {errorMessage && (
            <Alert
              variant="danger"
              title="Error creating user"
              isInline
              style={{marginBottom: '1em'}}
            >
              {errorMessage}
            </Alert>
          )}

          <FormGroup
            label="Username"
            isRequired
            fieldId="username"
            helperTextInvalid={errors.username?.message}
            validated={errors.username ? 'error' : 'default'}
          >
            <TextInput
              id="username"
              type="text"
              data-testid="username-input"
              validated={errors.username ? 'error' : 'default'}
              isDisabled={isLoading}
              {...register('username', {
                required: 'Username is required',
                minLength: {
                  value: 2,
                  message: 'Username must be at least 2 characters',
                },
                maxLength: {
                  value: 255,
                  message: 'Username must be less than 255 characters',
                },
                pattern: {
                  value: /^[a-z0-9_][a-z0-9_-]*$/,
                  message:
                    'Username must contain only lowercase letters, numbers, hyphens, and underscores',
                },
              })}
            />
          </FormGroup>

          <FormGroup
            label="Email"
            isRequired
            fieldId="email"
            helperTextInvalid={errors.email?.message}
            validated={errors.email ? 'error' : 'default'}
          >
            <TextInput
              id="email"
              type="email"
              data-testid="email-input"
              validated={errors.email ? 'error' : 'default'}
              isDisabled={isLoading}
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address',
                },
              })}
            />
          </FormGroup>
        </Form>
      )}
    </Modal>
  );
}
