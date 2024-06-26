import {AxiosResponse} from 'axios';
import {assertHttpCode} from './ErrorHandling';
import axios from 'src/libs/axios';
import {ISuperuserUsers} from 'src/hooks/UseSuperuserUsers';

export async function fetchSuperuserUsers() {
  const superuserUsersUrl = `/api/v1/superuser/users/`;
  const response: AxiosResponse = await axios.get(superuserUsersUrl);
  assertHttpCode(response.status, 200);
  return response.data?.users;
}

export async function createUser(name: string, email: string) {
  const createUserUrl = `/api/v1/superuser/users`;
  const reqBody = {name: name, email: email};
  const response = await axios.post(createUserUrl, reqBody);
  assertHttpCode(response.status, 201);
  return response.data;
}
