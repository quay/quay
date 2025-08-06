import axios from 'src/libs/axios';
import {AxiosResponse} from 'axios';
import {assertHttpCode} from './ErrorHandling';

export interface IChangeLogResponse {
  log: string;
}

export async function fetchChangeLog(): Promise<IChangeLogResponse> {
  const response: AxiosResponse<IChangeLogResponse> = await axios.get(
    '/api/v1/superuser/changelog/',
  );
  assertHttpCode(response.status, 200);
  return response.data;
}
