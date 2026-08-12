import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {enableTeamSyncForOrg, removeTeamSyncForOrg} from './TeamSyncResource';

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

describe('TeamSyncResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('enableTeamSyncForOrg', () => {
    it('sends group_name for oidc service', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await enableTeamSyncForOrg('myorg', 'devs', 'my-group', 'oidc');
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual({
        group_name: 'my-group',
      });
    });

    it('sends group_dn for ldap service', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await enableTeamSyncForOrg('myorg', 'devs', 'cn=devs,dc=example', 'ldap');
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual({
        group_dn: 'cn=devs,dc=example',
      });
    });

    it('sends group_id for keystone service', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await enableTeamSyncForOrg('myorg', 'devs', 'grp-123', 'keystone');
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual({
        group_id: 'grp-123',
      });
    });

    it('throws for unsupported service', async () => {
      await expect(
        enableTeamSyncForOrg('myorg', 'devs', 'grp', 'saml' as any),
      ).rejects.toThrow('Unsupported team sync service');
    });
  });

  describe('removeTeamSyncForOrg', () => {
    it('removes team sync', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse({}));

      await removeTeamSyncForOrg('myorg', 'devs');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/team/devs/syncing',
      );
    });
  });
});
