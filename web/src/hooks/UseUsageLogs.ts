import axios from 'src/libs/axios';
import {AxiosResponse} from 'axios';
import {assertHttpCode, ResourceError} from 'src/resources/ErrorHandling';

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

export async function getAggregateLogs(
  org: string,
  repo: string = null,
  starttime: string,
  endtime: string,
) {
  const url =
    repo != null
      ? `/api/v1/repository/${org}/${repo}/aggregatelogs`
      : `/api/v1/organization/${org}/aggregatelogs`;
  const response: AxiosResponse = await axios.get(url, {
    params: {starttime: `${starttime}`, endtime: `${endtime}`},
  });
  assertHttpCode(response.status, 200);
  return response.data.aggregated;
}

export async function getLogs(
  org: string,
  repo: string = null,
  starttime: string,
  endtime: string,
  next_page: string = null,
) {
  const url =
    repo != null
      ? `/api/v1/repository/${org}/${repo}/logs`
      : `/api/v1/organization/${org}/logs`;
  const response = await axios.get(url, {
    params: {
      starttime: `${starttime}`,
      endtime: `${endtime}`,
      next_page: next_page ? next_page : '',
    },
  });
  return {
    logs: response.data.logs,
    nextPage: response.data.next_page,
  };
}
