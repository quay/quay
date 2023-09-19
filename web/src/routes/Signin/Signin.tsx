import React, {useState} from 'react';
import {
  Alert,
  AlertActionCloseButton,
  LoginForm,
  LoginPage,
} from '@patternfly/react-core';
import logo from 'src/assets/quay.svg';
import {GlobalAuthState, loginUser} from 'src/resources/AuthResource';
import {useNavigate} from 'react-router-dom';
import {useRecoilState} from 'recoil';
import {AuthState} from 'src/atoms/AuthState';
import axios, {getCsrfToken} from 'src/libs/axios';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {AxiosError} from 'axios';
import './Signin.css';
import {addDisplayError} from 'src/resources/ErrorHandling';

export function Signin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [err, setErr] = useState<string>();
  const [, setAuthState] = useRecoilState(AuthState);

  const navigate = useNavigate();
  const quayConfig = useQuayConfig();

  let logoUrl = logo;
  if (quayConfig && quayConfig.config?.ENTERPRISE_DARK_LOGO_URL) {
    logoUrl = `${axios.defaults.baseURL}${quayConfig.config.ENTERPRISE_DARK_LOGO_URL}`;
  }

  const onLoginButtonClick = async (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent>,
  ) => {
    e.preventDefault();
    try {
      const response = await loginUser(username, password);
      if (response.success) {
        setAuthState((old) => ({...old, isSignedIn: true, username: username}));
        await getCsrfToken();
        GlobalAuthState.isLoggedIn = true;
        navigate('/organization');
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

  const loginForm = (
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
      loginButtonLabel="Log in"
    />
  );

  return (
    <LoginPage
      className={'pdf-u-background-color-100 pf-v5-u-text-align-left'}
      brandImgSrc={logoUrl}
      brandImgAlt="Red Hat Quay"
      backgroundImgSrc="assets/images/rh_login.jpeg"
      textContent="Quay builds, analyzes and distributes your container images. Store your containers with added security. Easily build and deploy new containers. Scan containers to provide security."
      loginTitle="Log in to your account"
    >
      {loginForm}
    </LoginPage>
  );
}
