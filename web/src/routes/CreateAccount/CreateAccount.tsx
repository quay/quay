import React, {useState} from 'react';
import {
  Alert,
  AlertActionCloseButton,
  Button,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  TextInput,
  ValidatedOptions,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {Link} from 'react-router-dom';
import './CreateAccount.css';
import {useCreateAccount} from 'src/hooks/UseCreateAccount';
import {LoginPageLayout} from 'src/components/LoginPageLayout';

export function CreateAccount() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const {createAccountWithAutoLogin, isLoading, error, setError} =
    useCreateAccount();

  const validateUsername = (username: string): ValidatedOptions => {
    if (!username) return ValidatedOptions.default;
    if (username.length < 3) return ValidatedOptions.error;
    if (!/^[a-zA-Z0-9][a-zA-Z0-9\-_.]*$/.test(username))
      return ValidatedOptions.error;
    return ValidatedOptions.success;
  };

  const validateEmail = (email: string): ValidatedOptions => {
    if (!email) return ValidatedOptions.default;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email)
      ? ValidatedOptions.success
      : ValidatedOptions.error;
  };

  const validatePassword = (password: string): ValidatedOptions => {
    if (!password) return ValidatedOptions.default;
    if (password.length < 8) return ValidatedOptions.error;
    return ValidatedOptions.success;
  };

  const validateConfirmPassword = (
    confirmPassword: string,
  ): ValidatedOptions => {
    if (!confirmPassword) return ValidatedOptions.default;
    return confirmPassword === password
      ? ValidatedOptions.success
      : ValidatedOptions.error;
  };

  const isFormValid = () => {
    return (
      validateUsername(username) === ValidatedOptions.success &&
      validateEmail(email) === ValidatedOptions.success &&
      validatePassword(password) === ValidatedOptions.success &&
      validateConfirmPassword(confirmPassword) === ValidatedOptions.success
    );
  };

  const onCreateAccountClick = async (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent>,
  ) => {
    e.preventDefault();
    if (!isFormValid()) {
      setError('Please fill in all fields correctly');
      return;
    }

    await createAccountWithAutoLogin(username, password, email);
  };

  const errMessage = (
    <Alert
      id="form-error-alert"
      isInline
      actionClose={<AlertActionCloseButton onClose={() => setError(null)} />}
      variant="danger"
      title={error}
    />
  );

  const createAccountForm = (
    <Form>
      <FormGroup
        label="Username"
        isRequired
        fieldId="username"
        validated={validateUsername(username)}
      >
        <TextInput
          isRequired
          type="text"
          id="username"
          name="username"
          value={username}
          onChange={(_event, v) => setUsername(v)}
          validated={validateUsername(username)}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem
              variant={
                validateUsername(username) === ValidatedOptions.error
                  ? 'error'
                  : 'default'
              }
              icon={
                validateUsername(username) === ValidatedOptions.error ? (
                  <ExclamationCircleIcon />
                ) : undefined
              }
            >
              Username must be at least 3 characters and contain only letters,
              numbers, hyphens, underscores, and periods
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup
        label="Email"
        isRequired
        fieldId="email"
        validated={validateEmail(email)}
      >
        <TextInput
          isRequired
          type="email"
          id="email"
          name="email"
          value={email}
          onChange={(_event, v) => setEmail(v)}
          validated={validateEmail(email)}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem
              variant={
                validateEmail(email) === ValidatedOptions.error
                  ? 'error'
                  : 'default'
              }
              icon={
                validateEmail(email) === ValidatedOptions.error ? (
                  <ExclamationCircleIcon />
                ) : undefined
              }
            >
              Please enter a valid email address
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup
        label="Password"
        isRequired
        fieldId="password"
        validated={validatePassword(password)}
      >
        <TextInput
          isRequired
          type="password"
          id="password"
          name="password"
          value={password}
          onChange={(_event, v) => setPassword(v)}
          validated={validatePassword(password)}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem
              variant={
                validatePassword(password) === ValidatedOptions.error
                  ? 'error'
                  : 'default'
              }
              icon={
                validatePassword(password) === ValidatedOptions.error ? (
                  <ExclamationCircleIcon />
                ) : undefined
              }
            >
              Password must be at least 8 characters long
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup
        label="Confirm Password"
        isRequired
        fieldId="confirm-password"
        validated={validateConfirmPassword(confirmPassword)}
      >
        <TextInput
          isRequired
          type="password"
          id="confirm-password"
          name="confirm-password"
          value={confirmPassword}
          onChange={(_event, v) => setConfirmPassword(v)}
          validated={validateConfirmPassword(confirmPassword)}
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem
              variant={
                validateConfirmPassword(confirmPassword) ===
                ValidatedOptions.error
                  ? 'error'
                  : 'default'
              }
              icon={
                validateConfirmPassword(confirmPassword) ===
                ValidatedOptions.error ? (
                  <ExclamationCircleIcon />
                ) : undefined
              }
            >
              Passwords must match
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      {error && errMessage}

      <FormGroup>
        <Button
          variant="primary"
          type="submit"
          isBlock
          isDisabled={!isFormValid() || isLoading}
          isLoading={isLoading}
          onClick={onCreateAccountClick}
        >
          Create Account
        </Button>
      </FormGroup>

      <FormGroup>
        <div style={{textAlign: 'center', marginTop: '16px'}}>
          Already have an account?{' '}
          <Link
            to="/signin"
            style={{color: 'var(--pf-v5-global--link--Color)'}}
          >
            Sign in
          </Link>
        </div>
      </FormGroup>
    </Form>
  );

  return (
    <LoginPageLayout
      title="Create Account"
      description="Create your Red Hat Quay account to start building, analyzing and distributing your container images with added security."
    >
      {createAccountForm}
    </LoginPageLayout>
  );
}
