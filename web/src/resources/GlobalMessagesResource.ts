import axios from 'src/libs/axios';
import {AxiosResponse} from 'axios';
import {assertHttpCode} from './ErrorHandling';

// Types based on API schema from endpoints/api/globalmessages.py
export interface IGlobalMessage {
  uuid: string;
  content: string;
  media_type: 'text/plain' | 'text/markdown';
  severity: 'info' | 'warning' | 'error';
}

export interface CreateGlobalMessageRequest {
  message: {
    content: string;
    media_type: 'text/plain' | 'text/markdown';
    severity: 'info' | 'warning' | 'error';
  };
}

export interface GlobalMessagesResponse {
  messages: IGlobalMessage[];
}

// API calls
export async function fetchGlobalMessages(): Promise<IGlobalMessage[]> {
  const response: AxiosResponse<GlobalMessagesResponse> =
    await axios.get('/api/v1/messages');
  assertHttpCode(response.status, 200);
  return response.data.messages || [];
}

export async function createGlobalMessage(
  messageData: CreateGlobalMessageRequest,
): Promise<void> {
  const response: AxiosResponse = await axios.post(
    '/api/v1/messages',
    messageData,
  );
  assertHttpCode(response.status, 201);
}

export async function deleteGlobalMessage(uuid: string): Promise<void> {
  const response: AxiosResponse = await axios.delete(`/api/v1/message/${uuid}`);
  assertHttpCode(response.status, 204);
}
