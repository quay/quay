import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

const signinApiUrl = '/api/v1/signin';
const signoutApiUrl = '/api/v1/signout';
const csrfTokenUrl = '/csrf_token';

interface AuthResource {
  isLoggedIn: boolean;
  csrfToken: string | null;
  bearerToken: string | null;
}

export const GlobalAuthState: AuthResource = {
  isLoggedIn: false,
  csrfToken: null,
  bearerToken: null,
};

export async function loginUser(username: string, password: string) {
  const response = await axios.post(signinApiUrl, {
    username: username,
    password: password,
  });
  if (response.data.success === true) {
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

export async function getUser(username: string) {
  const response = await axios.get(`api/v1/users/${username}`);
  return response;
}

export async function getOrganization(orgName: string) {
  const response = await axios.get(`api/v1/organization/${orgName}`);
  return response;
}

interface EmailVerificationRequest {
  code: string;
  username?: string;
}

interface ExternalLoginAuthRequest {
  kind: string;
}

export async function getExternalLoginAuthUrl(
  serviceId: string,
  action = 'login',
) {
  const response = await axios.post(`/api/v1/externallogin/${serviceId}`, {
    kind: action,
  });
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function detachExternalLogin(serviceId: string) {
  const response = await axios.post(`/api/v1/detachexternal/${serviceId}`);
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function verifyEmailAddress(data: EmailVerificationRequest) {
  const response = await axios.post('/api/v1/signin/verify', data);
  assertHttpCode(response.status, 200);
  return response.data;
}

interface VerifyUserRequest {
  password: string;
}

interface VerifyUserResponse {
  success: boolean;
}

export async function verifyUser(password: string) {
  const response = await axios.post<VerifyUserResponse>(
    '/api/v1/signin/verify',
    {password} as VerifyUserRequest,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}
