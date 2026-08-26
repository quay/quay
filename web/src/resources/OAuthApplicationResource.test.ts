import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchOAuthApplications,
  fetchOAuthApplicationTokens,
  createOAuthApplicationToken,
  assignOAuthApplicationTokenToUser,
  revokeOAuthApplicationToken,
  updateOAuthApplication,
  createOAuthApplication,
  resetOAuthApplicationClientSecret,
} from './OAuthApplicationResource';
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

describe('OAuthApplicationResource', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('fetchOAuthApplications', () => {
    it('fetches applications for an org', async () => {
      const applications = [{client_id: 'c1', name: 'app1'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({applications}));

      const result = await fetchOAuthApplications('myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/applications',
      );
      expect(result).toEqual(applications);
    });
  });

  describe('fetchOAuthApplicationTokens', () => {
    it('fetches tokens for an OAuth application', async () => {
      const tokens = [{uuid: 'token1', name: 'Inventory token'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({tokens}));

      const result = await fetchOAuthApplicationTokens('myorg', 'client1');

      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/applications/client1/tokens',
      );
      expect(result).toEqual(tokens);
    });

    it('recursively fetches paginated token results', async () => {
      const firstPage = [{uuid: 'token1'}];
      const secondPage = [{uuid: 'token2'}];
      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({tokens: firstPage, next_page: 'next/page'}),
        )
        .mockResolvedValueOnce(mockResponse({tokens: secondPage}));

      const result = await fetchOAuthApplicationTokens('myorg', 'client1');

      expect(axios.get).toHaveBeenNthCalledWith(
        1,
        '/api/v1/organization/myorg/applications/client1/tokens',
      );
      expect(axios.get).toHaveBeenNthCalledWith(
        2,
        '/api/v1/organization/myorg/applications/client1/tokens?next_page=next%2Fpage',
      );
      expect(result).toEqual([...firstPage, ...secondPage]);
    });

    it('does not wrap an error from a later page more than once', async () => {
      const requestError = new AxiosError('second page failed');
      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({tokens: [{uuid: 'token1'}], next_page: 'next'}),
        )
        .mockRejectedValueOnce(requestError);

      try {
        await fetchOAuthApplicationTokens('myorg', 'client1');
        expect.unreachable('should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ResourceError);
        expect((error as ResourceError).error).toBe(requestError);
      }
    });
  });

  describe('createOAuthApplicationToken', () => {
    it('creates a token for an OAuth application', async () => {
      const token = {
        uuid: 'token1',
        name: 'Generated token',
        token: 'secret-token',
      };
      const params = {
        name: 'Generated token',
        scope: 'repo:read',
        expiration: 3600,
      };
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(token));

      const result = await createOAuthApplicationToken(
        'myorg',
        'client1',
        params,
      );

      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/applications/client1/tokens',
        params,
      );
      expect(result).toEqual(token);
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        createOAuthApplicationToken('myorg', 'client1', {
          name: 'Generated token',
          scope: 'repo:read',
          expiration: 3600,
        }),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('assignOAuthApplicationTokenToUser', () => {
    it('assigns an OAuth token request to a user through the legacy assignment endpoint', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({message: 'Token assigned successfully'}),
      );

      const result = await assignOAuthApplicationTokenToUser('client1', {
        username: 'alice',
        scope: 'repo:read org:admin',
        redirect_uri: 'http://localhost/oauth/localapp',
      });

      expect(axios.post).toHaveBeenCalledWith(
        '/oauth/authorize/assignuser?username=alice&response_type=token&client_id=client1&scope=repo%3Aread+org%3Aadmin&redirect_uri=http%3A%2F%2Flocalhost%2Foauth%2Flocalapp&format=json',
      );
      expect(result).toEqual({message: 'Token assigned successfully'});
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        assignOAuthApplicationTokenToUser('client1', {
          username: 'alice',
          scope: 'repo:read',
          redirect_uri: 'http://localhost/oauth/localapp',
        }),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('revokeOAuthApplicationToken', () => {
    it('revokes a token for an OAuth application', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse({}, 204));

      await revokeOAuthApplicationToken('myorg', 'client1', 'token1');

      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/applications/client1/tokens/token1',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        revokeOAuthApplicationToken('myorg', 'client1', 'token1'),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('updateOAuthApplication', () => {
    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        updateOAuthApplication('myorg', 'c1', {name: 'new'}),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('createOAuthApplication', () => {
    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        createOAuthApplication('myorg', {name: 'app'} as any),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('resetOAuthApplicationClientSecret', () => {
    it('resets client secret', async () => {
      const app = {client_id: 'c1', client_secret: 'new_secret'};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(app));

      const result = await resetOAuthApplicationClientSecret('myorg', 'c1');
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain(
        'resetclientsecret',
      );
      expect(result).toEqual(app);
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        resetOAuthApplicationClientSecret('myorg', 'c1'),
      ).rejects.toThrow(ResourceError);
    });
  });
});
