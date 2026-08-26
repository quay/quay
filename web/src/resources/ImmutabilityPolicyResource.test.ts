import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchNamespaceImmutabilityPolicies,
  createNamespaceImmutabilityPolicy,
  deleteNamespaceImmutabilityPolicy,
  fetchRepositoryImmutabilityPolicies,
  createRepositoryImmutabilityPolicy,
  deleteRepositoryImmutabilityPolicy,
} from './ImmutabilityPolicyResource';

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

describe('ImmutabilityPolicyResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchNamespaceImmutabilityPolicies', () => {
    it('fetches namespace policies', async () => {
      const controller = new AbortController();
      const policies = [{uuid: 'p1', tagPattern: '*', tagPatternMatches: true}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({policies}));

      const result = await fetchNamespaceImmutabilityPolicies(
        'myorg',
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'organization/myorg/immutabilitypolicy',
      );
      expect(result).toEqual(policies);
    });
  });

  describe('createNamespaceImmutabilityPolicy', () => {
    it('creates a namespace policy', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({uuid: 'new-p1'}, 201),
      );

      const result = await createNamespaceImmutabilityPolicy('myorg', {
        tagPattern: 'release-*',
        tagPatternMatches: true,
      });
      expect(result).toEqual({uuid: 'new-p1'});
    });
  });

  describe('deleteNamespaceImmutabilityPolicy', () => {
    it('deletes a namespace policy', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse({}));

      await deleteNamespaceImmutabilityPolicy('myorg', 'p1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/immutabilitypolicy/p1',
      );
    });
  });

  describe('fetchRepositoryImmutabilityPolicies', () => {
    it('fetches repository policies', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({policies: []}));

      await fetchRepositoryImmutabilityPolicies(
        'org',
        'repo',
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'repository/org/repo/immutabilitypolicy',
      );
    });
  });

  describe('createRepositoryImmutabilityPolicy', () => {
    it('creates a repository policy', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({uuid: 'rp1'}, 201),
      );

      const result = await createRepositoryImmutabilityPolicy('org', 'repo', {
        tagPattern: 'v*',
        tagPatternMatches: true,
      });
      expect(result).toEqual({uuid: 'rp1'});
    });
  });

  describe('deleteRepositoryImmutabilityPolicy', () => {
    it('deletes a repository policy', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse({}));

      await deleteRepositoryImmutabilityPolicy('org', 'repo', 'rp1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/immutabilitypolicy/rp1',
      );
    });
  });
});
