import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  AutoPruneMethod,
  fetchNamespaceAutoPrunePolicies,
  createNamespaceAutoPrunePolicy,
  deleteNamespaceAutoPrunePolicy,
} from './NamespaceAutoPruneResource';

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

describe('NamespaceAutoPruneResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchNamespaceAutoPrunePolicies', () => {
    it('uses org endpoint for organizations', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({policies: []}));

      await fetchNamespaceAutoPrunePolicies('myorg', false, controller.signal);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'organization/myorg',
      );
    });

    it('uses user endpoint when isUser=true', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({policies: []}));

      await fetchNamespaceAutoPrunePolicies('user', true, controller.signal);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toBe(
        '/api/v1/user/autoprunepolicy/',
      );
    });
  });

  describe('createNamespaceAutoPrunePolicy', () => {
    it('creates a policy for an org', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createNamespaceAutoPrunePolicy(
        'myorg',
        {method: AutoPruneMethod.TAG_NUMBER, value: 5},
        false,
      );
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain(
        'organization/myorg',
      );
    });
  });

  describe('deleteNamespaceAutoPrunePolicy', () => {
    it('deletes a policy', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse({}));

      await deleteNamespaceAutoPrunePolicy('myorg', 'p1', false);
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/autoprunepolicy/p1',
      );
    });
  });

  describe('AutoPruneMethod enum', () => {
    it('has correct values', () => {
      expect(AutoPruneMethod.NONE).toBe('none');
      expect(AutoPruneMethod.TAG_NUMBER).toBe('number_of_tags');
      expect(AutoPruneMethod.TAG_CREATION_DATE).toBe('creation_date');
    });
  });
});
