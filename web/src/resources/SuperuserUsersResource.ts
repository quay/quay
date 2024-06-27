import {AxiosResponse} from 'axios';
import {ResourceError, assertHttpCode, throwIfError} from './ErrorHandling';
import axios from 'src/libs/axios';
import {ISuperuserUsers} from 'src/hooks/UseSuperuserUsers';

export async function fetchSuperuserUsers() {
  const superuserUsersUrl = `/api/v1/superuser/users/`;
  const response: AxiosResponse = await axios.get(superuserUsersUrl);
  assertHttpCode(response.status, 200);
  return response.data?.users;
}

export async function createUser(username: string, email: string) {
  const createUserUrl = `/api/v1/superuser/users`;
  const reqBody = {name: username, email: email};
  const response = await axios.post(createUserUrl, reqBody);
  assertHttpCode(response.status, 201);
  return response.data;
}

export async function deleteUser( username: string) {
  try {
    await axios.delete(`/api/v1/superuser/users/${username}`);
  } catch (error) {
    throw new ResourceError('Unable to delete user', username, error);
  }
}

export async function bulkDeleteUsers( users: ISuperuserUsers[]) {
  const responses = await Promise.allSettled(
    users.map((user) => deleteUser(user.username)),
  );
  throwIfError(responses, 'Error deleting users');
}
