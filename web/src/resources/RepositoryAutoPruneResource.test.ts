import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchRepositoryAutoPrunePolicies,
  createRepositoryAutoPrunePolicy,
  deleteRepositoryAutoPrunePolicy,
} from './RepositoryAutoPruneResource';
import {AutoPruneMethod} from './NamespaceAutoPruneResource';

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

describe('RepositoryAutoPruneResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchRepositoryAutoPrunePolicies', () => {
    it('fetches policies for a repository', async () => {
      const controller = new AbortController();
      const policies = [{uuid: 'p1', method: 'number_of_tags', value: 10}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({policies}));

      const result = await fetchRepositoryAutoPrunePolicies(
        'org',
        'repo',
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'autoprunepolicy',
      );
      expect(result).toEqual(policies);
    });
  });

  describe('createRepositoryAutoPrunePolicy', () => {
    it('creates a policy', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createRepositoryAutoPrunePolicy('org', 'repo', {
        method: AutoPruneMethod.TAG_NUMBER,
        value: 10,
      });
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/autoprunepolicy/',
        {method: 'number_of_tags', value: 10},
      );
    });
  });

  describe('deleteRepositoryAutoPrunePolicy', () => {
    it('deletes a policy', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse({}));

      await deleteRepositoryAutoPrunePolicy('org', 'repo', 'p1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/autoprunepolicy/p1',
      );
    });
  });
});
