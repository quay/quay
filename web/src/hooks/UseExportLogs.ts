import axios from 'src/libs/axios';
import {ResourceError} from 'src/resources/ErrorHandling';

export async function exportLogsForRepository(
  org: string,
  repo: string,
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

  try {
    const response = await axios.post(
      `/api/v1/repository/${org}/${repo}/exportlogs?starttime=${starttime}&endtime=${endtime}`,
      exportLogsCallback,
    );
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

export async function exportLogsForOrg(
  org: string,
  starttime: string,
  endtime: string,
  callback: string,
) {
  console.log('start' + starttime);
  console.log('end' + endtime);
  const exportLogsCallback = {};
  if (callback.includes('@')) {
    exportLogsCallback['callback_email'] = callback;
  } else {
    exportLogsCallback['callback_url'] = callback;
  }

  try {
    const response = await axios.post(
      `/api/v1/organization/${org}/exportlogs?starttime=${starttime}&endtime=${endtime}`,
      exportLogsCallback,
    );
    return response.data;
  } catch (error) {
    throw new ResourceError('Unable to export logs', `${callback}`, error);
  }
}
