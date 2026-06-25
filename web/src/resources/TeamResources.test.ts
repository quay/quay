import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  createNewTeamForNamespace,
  updateTeamForRobot,
  updateTeamDetailsForNamespace,
  updateTeamRepoPerm,
  fetchTeamsForNamespace,
  fetchTeamRepoPermsForOrg,
  deleteTeamForOrg,
  bulkDeleteTeams,
  TeamDeleteError,
} from './TeamResources';
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

describe('TeamResources', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('createNewTeamForNamespace', () => {
    it('creates a team with default member role', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await createNewTeamForNamespace('org', 'devs');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/org/team/devs',
        {name: 'devs', role: 'member'},
      );
    });

    it('includes description when provided', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await createNewTeamForNamespace('org', 'devs', 'Development team');
      expect(vi.mocked(axios.put).mock.calls[0][1]).toEqual({
        name: 'devs',
        role: 'member',
        description: 'Development team',
      });
    });
  });

  describe('updateTeamForRobot', () => {
    it('adds robot to team with org-prefixed name', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(
        mockResponse({name: 'org+bot'}),
      );

      const result = await updateTeamForRobot('org', 'devs', 'bot');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/org/team/devs/members/org+bot',
        {},
      );
      expect(result).toBe('org+bot');
    });
  });

  describe('updateTeamDetailsForNamespace', () => {
    it('updates team role', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({name: 'devs'}));

      await updateTeamDetailsForNamespace('org', 'devs', 'admin');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/org/team/devs',
        {name: 'devs', role: 'admin'},
      );
    });

    it('includes description when provided', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({name: 'devs'}));

      await updateTeamDetailsForNamespace(
        'org',
        'devs',
        'member',
        'Updated desc',
      );
      expect(vi.mocked(axios.put).mock.calls[0][1]).toHaveProperty(
        'description',
        'Updated desc',
      );
    });
  });

  describe('updateTeamRepoPerm', () => {
    it('updates repo permissions with PUT for non-none roles', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateTeamRepoPerm('org', 'devs', [
        {repoName: 'repo1', role: 'read'},
      ] as any);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo1/permissions/team/devs',
        {role: 'read'},
      );
    });

    it('uses DELETE for role=none', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await updateTeamRepoPerm('org', 'devs', [
        {repoName: 'repo1', role: 'none'},
      ] as any);
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo1/permissions/team/devs',
      );
    });
  });

  describe('fetchTeamsForNamespace', () => {
    it('fetches teams for an org', async () => {
      const teams = {devs: {name: 'devs', role: 'member'}};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({teams}));

      const result = await fetchTeamsForNamespace('org');
      expect(axios.get).toHaveBeenCalledWith('/api/v1/organization/org', {
        signal: undefined,
      });
      expect(result).toEqual(teams);
    });
  });

  describe('fetchTeamRepoPermsForOrg', () => {
    it('fetches team repo permissions', async () => {
      const permissions = [{repoName: 'repo1', role: 'read'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({permissions}));

      const result = await fetchTeamRepoPermsForOrg('org', 'devs');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/org/team/devs/permissions',
        {signal: undefined},
      );
      expect(result).toEqual(permissions);
    });
  });

  describe('deleteTeamForOrg', () => {
    it('deletes a team', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteTeamForOrg('org', 'devs');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/org/team/devs',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(deleteTeamForOrg('org', 'devs')).rejects.toThrow(
        ResourceError,
      );
    });
  });

  describe('bulkDeleteTeams', () => {
    it('deletes multiple teams', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await expect(
        bulkDeleteTeams('org', [{name: 'devs'}, {name: 'ops'}] as any),
      ).resolves.toBeUndefined();
    });
  });

  describe('TeamDeleteError', () => {
    it('stores team and error properties', () => {
      const axiosErr = new AxiosError('fail');
      const err = new TeamDeleteError('delete failed', 'devs', axiosErr);
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(TeamDeleteError);
      expect(err.team).toBe('devs');
      expect(err.error).toBe(axiosErr);
    });
  });
});
