import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchDefaultPermissions,
  updateDefaultPermission,
  deleteDefaultPermission,
  createDefaultPermission,
  addRepoPermissionToTeam,
  bulkDeleteDefaultPermissions,
} from './DefaultPermissionResource';
import {ResourceError} from './ErrorHandling';

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

describe('DefaultPermissionResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchDefaultPermissions', () => {
    it('fetches prototypes for an org', async () => {
      const prototypes = [{id: '1', role: 'read'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({prototypes}));

      const result = await fetchDefaultPermissions('myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/prototypes',
      );
      expect(result).toEqual(prototypes);
    });
  });

  describe('updateDefaultPermission', () => {
    it('updates permission role (lowercased)', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateDefaultPermission('myorg', 'perm1', 'Admin');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/prototypes/perm1',
        {id: 'perm1', role: 'admin'},
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        updateDefaultPermission('myorg', 'perm1', 'admin'),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('deleteDefaultPermission', () => {
    it('deletes a default permission', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteDefaultPermission('myorg', {
        id: 'perm1',
        createdBy: 'alice',
      } as any);
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/prototypes/perm1',
      );
    });
  });

  describe('createDefaultPermission', () => {
    it('creates a default permission', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      const permObj = {
        activating_user: {name: 'alice'},
        delegate: {name: 'bob', kind: 'user'},
        role: 'read',
      };
      await createDefaultPermission('myorg', permObj as any);
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/prototypes',
        permObj,
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        createDefaultPermission('myorg', {
          activating_user: {name: 'alice'},
        } as any),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('addRepoPermissionToTeam', () => {
    it('adds team permission (does not throw on error)', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await addRepoPermissionToTeam('org', 'repo', 'devs', 'Write');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/team/devs',
        {role: 'write'},
      );
    });

    it('catches errors without throwing', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(vi.fn());

      await expect(
        addRepoPermissionToTeam('org', 'repo', 'devs', 'Write'),
      ).resolves.toBeUndefined();
      consoleSpy.mockRestore();
    });
  });

  describe('bulkDeleteDefaultPermissions', () => {
    it('deletes multiple permissions', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await expect(
        bulkDeleteDefaultPermissions('myorg', [
          {id: 'p1', createdBy: 'alice'},
          {id: 'p2', createdBy: 'bob'},
        ] as any),
      ).resolves.toBeUndefined();
      expect(axios.delete).toHaveBeenCalledTimes(2);
      expect(axios.delete).toHaveBeenNthCalledWith(
        1,
        '/api/v1/organization/myorg/prototypes/p1',
      );
      expect(axios.delete).toHaveBeenNthCalledWith(
        2,
        '/api/v1/organization/myorg/prototypes/p2',
      );
    });
  });
});
