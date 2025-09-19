import React, {useState, useEffect} from 'react';
import {
  Alert,
  AlertActionCloseButton,
  Button,
  Form,
  FormGroup,
  LoginForm,
  LoginPage,
  Spinner,
  TextInput,
  ValidatedOptions,
} from '@patternfly/react-core';
import logo from 'src/assets/quay.svg';
import {GlobalAuthState, loginUser} from 'src/resources/AuthResource';
import {useNavigate, Link, useSearchParams} from 'react-router-dom';
import {useRecoilState} from 'recoil';
import {AuthState} from 'src/atoms/AuthState';
import axios, {getCsrfToken} from 'src/libs/axios';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {AxiosError} from 'axios';
import './Signin.css';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {usePasswordRecovery} from 'src/hooks/UsePasswordRecovery';
import {useQuayState} from 'src/hooks/UseQuayState';
import {ReCaptcha} from 'src/components/ReCaptcha';

type ViewType = 'signin' | 'forgotPassword';

export function Signin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [err, setErr] = useState<string>();
  const [, setAuthState] = useRecoilState(AuthState);

  const [currentView, setCurrentView] = useState<ViewType>('signin');
  const [recoveryEmail, setRecoveryEmail] = useState('');
  const [recaptchaToken, setRecaptchaToken] = useState<string | null>(null);

  const {inReadOnlyMode, inAccountRecoveryMode} = useQuayState();

  const navigate = useNavigate();
  const quayConfig = useQuayConfig();
  const [searchParams] = useSearchParams();
  const {
    requestRecovery,
    isLoading: sendingRecovery,
    error: recoveryError,
    result: recoverySent,
    setError: setRecoveryError,
  } = usePasswordRecovery();

  let logoUrl = logo;
  if (quayConfig && quayConfig.config?.ENTERPRISE_DARK_LOGO_URL) {
    logoUrl = `${axios.defaults.baseURL}${quayConfig.config.ENTERPRISE_DARK_LOGO_URL}`;
  }

  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = `${quayConfig.config.REGISTRY_TITLE} • Quay`;
    }
  }, [quayConfig]);

  const showForgotPassword = () => {
    if (!quayConfig) return false;
    return (
      quayConfig.features?.MAILING === true &&
      quayConfig.config?.AUTHENTICATION_TYPE === 'Database' &&
      quayConfig.features?.DIRECT_LOGIN === true
    );
  };

  const showCreateAccount = () => {
    if (!quayConfig) return false;
    return (
      !inReadOnlyMode &&
      quayConfig.features?.USER_CREATION === true &&
      quayConfig.config?.AUTHENTICATION_TYPE === 'Database' &&
      quayConfig.features?.DIRECT_LOGIN === true &&
      !quayConfig.features?.INVITE_ONLY_USER_CREATION &&
      !inAccountRecoveryMode
    );
  };

  const showInvitationMessage = () => {
    if (!quayConfig) return false;
    return (
      quayConfig.features?.USER_CREATION === true &&
      quayConfig.config?.AUTHENTICATION_TYPE === 'Database' &&
      quayConfig.features?.DIRECT_LOGIN === true &&
      quayConfig.features?.INVITE_ONLY_USER_CREATION === true
    );
  };

  const handleSendRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recoveryEmail) return;

    try {
      await requestRecovery(recoveryEmail, recaptchaToken);
    } catch (error) {
      // Error is handled by the hook
    }
  };

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
    if (view === 'signin') {
      setRecoveryError(null);
      setRecaptchaToken(null);
    } else {
      setErr(undefined);
    }
  };

  const onLoginButtonClick = async (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent>,
  ) => {
    e.preventDefault();
    try {
      const response = await loginUser(username, password);
      if (response.success === true) {
        setAuthState((old) => ({...old, isSignedIn: true, username: username}));
        await getCsrfToken();
        GlobalAuthState.isLoggedIn = true;
        const redirectUrl = searchParams.get('redirect_url');
        if (redirectUrl) {
          window.location.href = redirectUrl;
        } else {
          navigate('/organization');
        }
      } else {
        setErr('Invalid login credentials');
      }
    } catch (err) {
      const authErr =
        err instanceof AxiosError &&
        err.response &&
        err.response.status === 403;
      if (authErr && err.response.data.invalidCredentials) {
        setErr('Invalid login credentials');
      } else if (authErr) {
        setErr('CSRF token expired - please refresh');
      } else {
        setErr(addDisplayError('Unable to sign in', err));
      }
    }
  };

  const errMessage = (
    <Alert
      id="form-error-alert"
      isInline
      actionClose={<AlertActionCloseButton onClose={() => setErr(null)} />}
      variant="danger"
      title={err}
    />
  );

  const loginButtonLabel = quayConfig?.config?.REGISTRY_TITLE
    ? `Sign in to ${quayConfig.config.REGISTRY_TITLE}`
    : 'Sign in';

  const recoveryForm = (
    <Form onSubmit={handleSendRecovery} className="forgot-password-form">
      {!sendingRecovery && !recoverySent && (
        <h4>Please enter the e-mail address for your account to recover it</h4>
      )}

      {sendingRecovery && (
        <div style={{textAlign: 'center', margin: '20px 0'}}>
          <Spinner size="lg" />
        </div>
      )}

      {!sendingRecovery && (
        <>
          {recoverySent?.status === 'sent' && (
            <Alert
              variant="success"
              isInline
              title=""
              style={{marginBottom: '20px'}}
            >
              Instructions on how to reset your password have been sent to{' '}
              {recoveryEmail}. If you do not receive the email, please try again
              shortly.
            </Alert>
          )}

          {recoverySent?.status === 'org' && (
            <Alert
              variant="info"
              isInline
              title=""
              style={{marginBottom: '20px'}}
            >
              The e-mail address <code>{recoverySent.orgemail}</code> is
              assigned to organization <code>{recoverySent.orgname}</code>. To
              access that organization, an admin user must be used.
              <br />
              <br />
              An e-mail has been sent to <code>
                {recoverySent.orgemail}
              </code>{' '}
              with the full list of admin users.
            </Alert>
          )}

          {recoveryError && (
            <Alert
              variant="danger"
              isInline
              actionClose={
                <AlertActionCloseButton
                  onClose={() => setRecoveryError(null)}
                />
              }
              title={recoveryError}
              style={{marginBottom: '20px'}}
            />
          )}

          {!recoverySent && (
            <>
              <FormGroup label="" fieldId="recovery-email">
                <TextInput
                  isRequired
                  type="email"
                  id="recovery-email"
                  name="recovery-email"
                  value={recoveryEmail}
                  onChange={(_event, v) => setRecoveryEmail(v)}
                  placeholder="Email"
                  validated={
                    recoveryEmail &&
                    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recoveryEmail)
                      ? ValidatedOptions.error
                      : ValidatedOptions.default
                  }
                />
              </FormGroup>

              <ReCaptcha onChange={setRecaptchaToken} className="captcha" />

              <Button
                variant="primary"
                type="submit"
                isBlock
                isDisabled={
                  !recoveryEmail ||
                  !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recoveryEmail) ||
                  sendingRecovery
                }
                style={{marginTop: '20px'}}
              >
                Send Recovery Email
              </Button>
            </>
          )}
        </>
      )}

      <div style={{textAlign: 'center', marginTop: '16px'}}>
        <button
          type="button"
          className="signin-link-button"
          onClick={() => handleViewChange('signin')}
        >
          Back to Sign In
        </button>
      </div>
    </Form>
  );

  const loginForm = (
    <>
      <LoginForm
        showHelperText={err != null}
        helperText={errMessage}
        usernameLabel="Username"
        usernameValue={username}
        onChangeUsername={(_event, v) => setUsername(v)}
        isValidUsername={true}
        passwordLabel="Password"
        passwordValue={password}
        onChangePassword={(_event, v) => setPassword(v)}
        isValidPassword={true}
        isRememberMeChecked={rememberMe}
        onChangeRememberMe={(_event, v) => setRememberMe(v)}
        onLoginButtonClick={(e) => onLoginButtonClick(e)}
        loginButtonLabel={loginButtonLabel}
      />
      <div className="signin-form-links">
        {showCreateAccount() && (
          <>
            Don&apos;t have an account?{' '}
            <Link
              to="/createaccount"
              style={{color: 'var(--pf-v5-global--link--Color)'}}
            >
              Create account
            </Link>
            <br />
          </>
        )}

        {showInvitationMessage() && (
          <>
            <span>Invitation required to sign up</span>
            <br />
          </>
        )}

        {showForgotPassword() && currentView !== 'forgotPassword' && (
          <button
            type="button"
            className="signin-link-button"
            onClick={() => handleViewChange('forgotPassword')}
          >
            Forgot Password?
          </button>
        )}

        {currentView === 'forgotPassword' && (
          <button
            type="button"
            className="signin-link-button"
            onClick={() => handleViewChange('signin')}
          >
            Back to Sign In
          </button>
        )}
      </div>
    </>
  );

  return (
    <LoginPage
      className={'pdf-u-background-color-100 pf-v5-u-text-align-left'}
      brandImgSrc={logoUrl}
      brandImgAlt="Red Hat Quay"
      backgroundImgSrc="assets/images/rh_login.jpeg"
      textContent="Quay builds, analyzes and distributes your container images. Store your containers with added security. Easily build and deploy new containers. Scan containers to provide security."
      loginTitle={
        currentView === 'signin' ? 'Log in to your account' : 'Reset Password'
      }
    >
      {currentView === 'signin' ? loginForm : recoveryForm}
    </LoginPage>
  );
}
