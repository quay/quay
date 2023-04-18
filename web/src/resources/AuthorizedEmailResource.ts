import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {assertHttpCode} from './ErrorHandling';

export interface AuthorizedEmail {
  email: string;
  repo: string;
  namespace: string;
  confirmed: boolean;
}

export async function fetchAuthorizedEmail(
  org: string,
  repo: string,
  email: string,
) {
  const url = `/api/v1/repository/${org}/${repo}/authorizedemail/${email}`;
  const response: AxiosResponse<AuthorizedEmail> = await axios.get(url);
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function sendAuthorizedEmail(
  org: string,
  repo: string,
  email: string,
) {
  const url = `/api/v1/repository/${org}/${repo}/authorizedemail/${email}`;
  const response: AxiosResponse<AuthorizedEmail> = await axios.post(url);
  assertHttpCode(response.status, 200);
  return response.data;
}
