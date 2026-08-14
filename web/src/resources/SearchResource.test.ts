import {fetchSearchResults, fetchSearchSuggestions} from './SearchResource';
import axios from 'src/libs/axios';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = vi.mocked(axios.get);

describe('SearchResource', () => {
  afterEach(() => vi.clearAllMocks());

  describe('fetchSearchResults', () => {
    it('calls /api/v1/find/repositories with correct params', async () => {
      const mockResponse = {
        status: 200,
        data: {
          results: [],
          has_additional: false,
          page: 1,
          page_size: 10,
          start_index: 0,
        },
      };
      mockGet.mockResolvedValue(mockResponse);

      const result = await fetchSearchResults('test', 2);

      expect(mockGet).toHaveBeenCalledWith('/api/v1/find/repositories', {
        params: {query: 'test', page: 2, includeUsage: true},
      });
      expect(result.results).toEqual([]);
      expect(result.page).toBe(1);
    });

    it('defaults page to 1', async () => {
      mockGet.mockResolvedValue({
        status: 200,
        data: {
          results: [],
          has_additional: false,
          page: 1,
          page_size: 10,
          start_index: 0,
        },
      });

      await fetchSearchResults('query');

      expect(mockGet).toHaveBeenCalledWith('/api/v1/find/repositories', {
        params: {query: 'query', page: 1, includeUsage: true},
      });
    });

    it('throws on non-200 status', async () => {
      mockGet.mockResolvedValue({status: 500, data: {}});

      await expect(fetchSearchResults('test')).rejects.toThrow(
        'Unexpected HTTP status code: 500',
      );
    });
  });

  describe('fetchSearchSuggestions', () => {
    it('calls /api/v1/find/all with query param', async () => {
      const mockResponse = {
        status: 200,
        data: {results: [{kind: 'repository', name: 'test-repo', score: 4}]},
      };
      mockGet.mockResolvedValue(mockResponse);

      const result = await fetchSearchSuggestions('test');

      expect(mockGet).toHaveBeenCalledWith('/api/v1/find/all', {
        params: {query: 'test'},
      });
      expect(result.results).toHaveLength(1);
    });

    it('throws on non-200 status', async () => {
      mockGet.mockResolvedValue({status: 403, data: {}});

      await expect(fetchSearchSuggestions('test')).rejects.toThrow(
        'Unexpected HTTP status code: 403',
      );
    });
  });
});
