import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchUser,
  fetchUsersAsSuperUser,
  getEntityKind,
  fetchEntities,
  createUser,
  createSuperuserUser,
  updateSuperuserUser,
  deleteSuperuserUser,
  updateUser,
  createClientKey,
  convert,
  deleteUser,
  UserDeleteError,
  ApplicationTokenError,
  fetchApplicationTokens,
  createApplicationToken,
  fetchApplicationToken,
  revokeApplicationToken,
  sendRecoveryEmail,
  EntityKind,
  Entity,
} from './UserResource';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

/** Creates a mock Axios response with the given data and status. */
function mockResponse(data: unknown, status = 200): AxiosResponse {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  };
}

describe('UserResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchUser', () => {
    it('fetches the current user', async () => {
      const user = {username: 'testuser', anonymous: false};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(user));

      const result = await fetchUser();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/user/');
      expect(result).toEqual(user);
    });
  });

  describe('fetchUsersAsSuperUser', () => {
    it('returns users array', async () => {
      const users = [{username: 'u1'}, {username: 'u2'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({users}));

      const result = await fetchUsersAsSuperUser();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/superuser/users/');
      expect(result).toEqual(users);
    });
  });

  describe('getEntityKind', () => {
    it('returns team for team entities', () => {
      const entity: Entity = {name: 'devs', kind: EntityKind.team};
      expect(getEntityKind(entity)).toBe(EntityKind.team);
    });

    it('returns robot for user entities with is_robot=true', () => {
      const entity: Entity = {
        name: 'org+bot',
        kind: EntityKind.user,
        is_robot: true,
      };
      expect(getEntityKind(entity)).toBe(EntityKind.robot);
    });

    it('returns user for user entities without is_robot', () => {
      const entity: Entity = {name: 'alice', kind: EntityKind.user};
      expect(getEntityKind(entity)).toBe(EntityKind.user);
    });

    it('returns undefined for unknown entity kind', () => {
      const entity: Entity = {
        name: 'unknown',
        kind: 'other' as EntityKind,
      };
      expect(getEntityKind(entity)).toBeUndefined();
    });
  });

  describe('fetchEntities', () => {
    it('fetches entities for a namespace', async () => {
      const results = [{name: 'user1', kind: 'user'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({results}));

      const result = await fetchEntities('user', 'myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/entities/user?namespace=myorg',
      );
      expect(result).toEqual(results);
    });

    it('includes teams in search when includeTeams=true', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({results: []}));

      await fetchEntities('alice', 'myorg', true);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'includeTeams=true',
      );
    });

    it('strips prefix before + for robot account searches', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({results: []}));

      await fetchEntities('org+mybot', 'myorg');
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        '/api/v1/entities/mybot',
      );
    });

    it('filters out robots when includeRobots=false', async () => {
      const results = [
        {name: 'alice', kind: EntityKind.user, is_robot: false},
        {name: 'org+bot', kind: EntityKind.user, is_robot: true},
        {name: 'devs', kind: EntityKind.team},
      ];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({results}));

      const result = await fetchEntities('a', 'myorg', false, false);
      expect(result).toHaveLength(2);
      expect(
        result.every((e) => !e.is_robot || e.kind !== EntityKind.user),
      ).toBe(true);
    });

    it('returns empty array when results is missing', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({}));

      const result = await fetchEntities('x', 'myorg');
      expect(result).toEqual([]);
    });
  });

  describe('createUser', () => {
    it('creates a user account', async () => {
      const response = {awaiting_verification: true};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(response));

      const result = await createUser('alice', 'pass123', 'alice@test.com');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/user/', {
        username: 'alice',
        password: 'pass123',
        email: 'alice@test.com',
      });
      expect(result).toEqual(response);
    });
  });

  describe('createSuperuserUser', () => {
    it('creates a user as superuser', async () => {
      const response = {
        username: 'bob',
        email: 'bob@test.com',
        password: 'gen',
        enabled: true,
      };
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(response));

      const result = await createSuperuserUser({
        username: 'bob',
        email: 'bob@test.com',
      });
      expect(axios.post).toHaveBeenCalledWith('/api/v1/superuser/users/', {
        username: 'bob',
        email: 'bob@test.com',
      });
      expect(result).toEqual(response);
    });
  });

  describe('updateSuperuserUser', () => {
    it('updates a user as superuser', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateSuperuserUser('bob', {enabled: false});
      expect(axios.put).toHaveBeenCalledWith('/api/v1/superuser/users/bob', {
        enabled: false,
      });
    });
  });

  describe('deleteSuperuserUser', () => {
    it('deletes a user as superuser', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteSuperuserUser('bob');
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/superuser/users/bob');
    });
  });

  describe('updateUser', () => {
    it('updates current user settings', async () => {
      const user = {username: 'alice', email: 'new@test.com'};
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse(user));

      const result = await updateUser({email: 'new@test.com'});
      expect(axios.put).toHaveBeenCalledWith('api/v1/user/', {
        email: 'new@test.com',
      });
      expect(result).toEqual(user);
    });
  });

  describe('createClientKey', () => {
    it('returns the generated key', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({key: 'abc123'}),
      );

      const result = await createClientKey('mypassword');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/user/clientkey', {
        password: 'mypassword',
      });
      expect(result).toBe('abc123');
    });
  });

  describe('convert', () => {
    it('converts user account', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await convert({adminUser: 'admin', adminPassword: 'pass'});
      expect(axios.post).toHaveBeenCalledWith('/api/v1/user/convert', {
        adminUser: 'admin',
        adminPassword: 'pass',
      });
    });
  });

  describe('deleteUser', () => {
    it('deletes the current user account', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await expect(deleteUser()).resolves.toBeUndefined();
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/user/');
    });

    it('throws UserDeleteError on failure', async () => {
      const axiosErr = new AxiosError('Server Error');
      (axiosErr as any).response = {data: {detail: 'Cannot delete'}};
      vi.mocked(axios.delete).mockRejectedValueOnce(axiosErr);

      try {
        await deleteUser();
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(UserDeleteError);
        expect((err as UserDeleteError).message).toContain('Cannot delete');
      }
    });
  });

  describe('UserDeleteError', () => {
    it('extracts detail from API response', () => {
      const axiosErr = new AxiosError('Request failed');
      (axiosErr as any).response = {data: {detail: 'user has repos'}};
      const err = new UserDeleteError('Delete failed', 'alice', axiosErr);
      expect(err.message).toContain('user has repos');
      expect(err.username).toBe('alice');
    });

    it('falls back to error.message when no detail', () => {
      const axiosErr = new AxiosError('Network Error');
      const err = new UserDeleteError('Delete failed', 'alice', axiosErr);
      expect(err.message).toContain('Network Error');
    });
  });

  describe('ApplicationTokenError', () => {
    it('stores tokenId and extracts API detail', () => {
      const axiosErr = new AxiosError('fail');
      (axiosErr as any).response = {data: {detail: 'token expired'}};
      const err = new ApplicationTokenError('Token error', 'tok-123', axiosErr);
      expect(err.tokenId).toBe('tok-123');
      expect(err.message).toContain('token expired');
    });
  });

  describe('fetchApplicationTokens', () => {
    it('returns tokens response', async () => {
      const response = {
        tokens: [{uuid: '1', title: 'test'}],
        only_expiring: false,
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(response));

      const result = await fetchApplicationTokens();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/user/apptoken');
      expect(result).toEqual(response);
    });

    it('throws ApplicationTokenError on failure', async () => {
      vi.mocked(axios.get).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(fetchApplicationTokens()).rejects.toThrow(
        ApplicationTokenError,
      );
    });
  });

  describe('createApplicationToken', () => {
    it('creates token with title', async () => {
      const response = {token: {uuid: '1', title: 'My Token'}};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(response));

      const result = await createApplicationToken('My Token');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/user/apptoken', {
        title: 'My Token',
      });
      expect(result).toEqual(response);
    });

    it('throws ApplicationTokenError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(createApplicationToken('test')).rejects.toThrow(
        ApplicationTokenError,
      );
    });
  });

  describe('fetchApplicationToken', () => {
    it('returns a specific token', async () => {
      const token = {uuid: 'tok-1', title: 'test', token_code: 'secret'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({token}));

      const result = await fetchApplicationToken('tok-1');
      expect(axios.get).toHaveBeenCalledWith('/api/v1/user/apptoken/tok-1');
      expect(result).toEqual(token);
    });

    it('throws ApplicationTokenError on failure', async () => {
      vi.mocked(axios.get).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(fetchApplicationToken('tok-1')).rejects.toThrow(
        ApplicationTokenError,
      );
    });
  });

  describe('revokeApplicationToken', () => {
    it('deletes a token by uuid', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await revokeApplicationToken('tok-1');
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/user/apptoken/tok-1');
    });

    it('throws ApplicationTokenError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(revokeApplicationToken('tok-1')).rejects.toThrow(
        ApplicationTokenError,
      );
    });
  });

  describe('sendRecoveryEmail', () => {
    it('sends recovery email for a user', async () => {
      const response = {email: 'alice@test.com'};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(response));

      const result = await sendRecoveryEmail('alice');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/superusers/users/alice/sendrecovery',
      );
      expect(result).toEqual(response);
    });
  });
});
