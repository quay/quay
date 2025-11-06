import {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  Button,
  Alert,
} from '@patternfly/react-core';
import {useForm} from 'react-hook-form';
import {useCreateUser} from 'src/hooks/UseCreateUser';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface CreateUserFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export function CreateUserModal(props: CreateUserModalProps) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {
    register,
    handleSubmit,
    formState: {errors, isValid},
    watch,
    reset,
  } = useForm<CreateUserFormData>({
    mode: 'onChange',
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const {createUser, isLoading} = useCreateUser({
    onSuccess: (username: string) => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created user ${username}`,
      });
      reset();
      setErrorMessage(null);
      props.onSuccess();
    },
    onError: (error: string) => {
      setErrorMessage(error);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to create user',
        message: error,
      });
    },
  });

  const password = watch('password');

  const onSubmit = (data: CreateUserFormData) => {
    setErrorMessage(null);
    createUser({
      username: data.username,
      email: data.email,
      password: data.password,
    });
  };

  const handleClose = () => {
    reset();
    setErrorMessage(null);
    props.onClose();
  };

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Create New User"
      isOpen={props.isOpen}
      onClose={handleClose}
      data-testid="create-user-modal"
      actions={[
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
      ]}
    >
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

        <FormGroup
          label="Password"
          isRequired
          fieldId="password"
          helperTextInvalid={errors.password?.message}
          validated={errors.password ? 'error' : 'default'}
        >
          <TextInput
            id="password"
            type="password"
            data-testid="password-input"
            validated={errors.password ? 'error' : 'default'}
            isDisabled={isLoading}
            {...register('password', {
              required: 'Password is required',
              minLength: {
                value: 8,
                message: 'Password must be at least 8 characters',
              },
            })}
          />
        </FormGroup>

        <FormGroup
          label="Confirm Password"
          isRequired
          fieldId="confirmPassword"
          helperTextInvalid={errors.confirmPassword?.message}
          validated={errors.confirmPassword ? 'error' : 'default'}
        >
          <TextInput
            id="confirmPassword"
            type="password"
            data-testid="confirm-password-input"
            validated={errors.confirmPassword ? 'error' : 'default'}
            isDisabled={isLoading}
            {...register('confirmPassword', {
              required: 'Please confirm your password',
              validate: (value) =>
                value === password || 'Passwords do not match',
            })}
          />
        </FormGroup>
      </Form>
    </Modal>
  );
}
