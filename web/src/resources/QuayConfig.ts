// import { getBackendUrl } from '../utils/httputils';

import {AxiosResponse} from 'axios';
import axios from '../libs/axios';
import {assertHttpCode} from './ErrorHandling';

export async function fetchQuayConfig() {
  // TODO: Add response type to AxiosResponse
  const response: AxiosResponse = await axios.get('/config');
  assertHttpCode(response.status, 200);
  return response.data;
}
