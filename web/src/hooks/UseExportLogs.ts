import axios from 'src/libs/axios';
import {ResourceError} from 'src/resources/ErrorHandling';

export async function exportLogs(
  org: string,
  repo: string = null,
  starttime: string,
  endtime: string,
  callback: string,
) {
  const exportLogsCallback = {};
  if (callback.includes('@')) {
    exportLogsCallback['callback_email'] = callback;
  } else {
    exportLogsCallback['callback_url'] = callback;
  }

  const url = repo
    ? `/api/v1/repository/${org}/${repo}/exportlogs?starttime=${starttime}&endtime=${endtime}`
    : `/api/v1/organization/${org}/exportlogs?starttime=${starttime}&endtime=${endtime}`;

  try {
    const response = await axios.post(url, exportLogsCallback);
    return response.data;
  } catch (error) {
    if (error.response) {
      return error.response.data;
    } else {
      throw new ResourceError(
        'Unable to export logs',
        error.response.status,
        error.response.data,
      );
    }
  }
}
