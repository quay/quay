import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

const signinApiUrl = '/api/v1/signin';
const signoutApiUrl = '/api/v1/signout';
const csrfTokenUrl = '/csrf_token';

interface AuthResource {
  isLoggedIn: boolean;
  csrfToken: string | null;
}

export const GlobalAuthState: AuthResource = {
  isLoggedIn: false,
  csrfToken: null,
};

export async function loginUser(username: string, password: string) {
  const response = await axios.post(signinApiUrl, {
    username: username,
    password: password,
  });
  if (response.data == 'success') {
    GlobalAuthState.isLoggedIn = true;
    GlobalAuthState.csrfToken = undefined;
  }
  return response.data;
}

export async function logoutUser() {
  const response = await axios.post(signoutApiUrl);
  assertHttpCode(response.status, 200);
  GlobalAuthState.isLoggedIn = false;
  GlobalAuthState.csrfToken = undefined;
  return response.data;
}

export async function getCsrfToken() {
  const response = await axios.get(csrfTokenUrl);
  assertHttpCode(response.status, 200);
  GlobalAuthState.csrfToken = response.data.csrf_token;
  return response.data;
}
