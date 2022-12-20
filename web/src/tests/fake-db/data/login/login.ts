import {AxiosRequestConfig} from 'axios';
import {mock} from 'src/tests/fake-db/MockAxios';

const response = {
  success: true,
};

const csrfResponse = {
  csrf_token: 'test-csrf-token',
};

mock.onPost('/api/v1/signin').reply((request: AxiosRequestConfig) => {
  const {username, password} = JSON.parse(request.data);
  return [200, response];
});

mock.onGet('/csrf_token').reply((request: AxiosRequestConfig) => {
  return [200, csrfResponse];
});
