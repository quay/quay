import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  getTags,
  getLabels,
  createLabel,
  deleteLabel,
  bulkCreateLabels,
  bulkDeleteLabels,
  bulkDeleteTags,
  deleteTag,
  expireTag,
  TagDeleteError,
  getManifestByDigest,
  getSecurityDetails,
  createTag,
  setExpiration,
  bulkSetExpiration,
  setTagImmutability,
  bulkSetTagImmutability,
  restoreTag,
  permanentlyDeleteTag,
  getTagPullStatistics,
  Label,
} from './TagResource';
import {BulkOperationError, ResourceError} from './ErrorHandling';

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

describe('TagResource', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    // Reset window.location.search for getTags tests
    Object.defineProperty(window, 'location', {
      value: {search: '', protocol: 'https:', host: 'localhost'},
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
  });

  describe('getTags', () => {
    it('fetches tags with default parameters', async () => {
      const tagsResponse = {page: 1, has_additional: false, tags: []};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(tagsResponse));

      const result = await getTags('org', 'repo', 1);
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/?limit=100&page=1&onlyActiveTags=true',
      );
      expect(result).toEqual(tagsResponse);
    });

    it('appends specificTag when provided', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({page: 1, has_additional: false, tags: []}),
      );

      await getTags('org', 'repo', 1, 50, 'v1.0');
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'specificTag=v1.0',
      );
    });

    it('omits onlyActiveTags when set to false', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({page: 1, has_additional: false, tags: []}),
      );

      await getTags('org', 'repo', 1, 100, null, false);
      expect(vi.mocked(axios.get).mock.calls[0][0]).not.toContain(
        'onlyActiveTags',
      );
    });

    it('appends filter_tag_name from URL search params', async () => {
      Object.defineProperty(window, 'location', {
        value: {
          search: '?filter_tag_name=latest',
          protocol: 'https:',
          host: 'localhost',
        },
        writable: true,
        configurable: true,
      });
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({page: 1, has_additional: false, tags: []}),
      );

      await getTags('org', 'repo', 1);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'filter_tag_name=latest',
      );
    });
  });

  describe('getLabels', () => {
    it('fetches labels for a manifest digest', async () => {
      const labels = [{key: 'env', value: 'prod'}];
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({labels}));

      const result = await getLabels(
        'org',
        'repo',
        'sha256:abc',
        controller.signal,
      );
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/manifest/sha256:abc/labels',
        {signal: controller.signal},
      );
      expect(result).toEqual(labels);
    });
  });

  describe('createLabel', () => {
    it('creates a label on a manifest', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      const label: Label = {
        key: 'env',
        value: 'prod',
        media_type: 'text/plain',
      };
      await expect(
        createLabel('org', 'repo', 'sha256:abc', label),
      ).resolves.toBeUndefined();
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/manifest/sha256:abc/labels',
        {key: 'env', value: 'prod', media_type: 'text/plain'},
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      const label: Label = {key: 'env', value: 'prod'};
      await expect(
        createLabel('org', 'repo', 'sha256:abc', label),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('deleteLabel', () => {
    it('deletes a label by id', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      const label: Label = {id: 'label-1', key: 'env', value: 'prod'};
      await expect(
        deleteLabel('org', 'repo', 'sha256:abc', label),
      ).resolves.toBeUndefined();
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/manifest/sha256:abc/labels/label-1',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      const label: Label = {id: 'label-1', key: 'env', value: 'prod'};
      await expect(
        deleteLabel('org', 'repo', 'sha256:abc', label),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('bulkCreateLabels', () => {
    it('creates multiple labels via Promise.allSettled', async () => {
      vi.mocked(axios.post)
        .mockResolvedValueOnce(mockResponse({}, 201))
        .mockResolvedValueOnce(mockResponse({}, 201));

      const labels: Label[] = [
        {key: 'a', value: '1'},
        {key: 'b', value: '2'},
      ];
      await expect(
        bulkCreateLabels('org', 'repo', 'sha256:abc', labels),
      ).resolves.toBeUndefined();
    });
  });

  describe('bulkDeleteLabels', () => {
    it('deletes multiple labels via Promise.allSettled', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      const labels: Label[] = [
        {id: '1', key: 'a', value: '1'},
        {id: '2', key: 'b', value: '2'},
      ];
      await expect(
        bulkDeleteLabels('org', 'repo', 'sha256:abc', labels),
      ).resolves.toBeUndefined();
    });
  });

  describe('deleteTag', () => {
    it('deletes a tag successfully', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await expect(deleteTag('org', 'repo', 'latest')).resolves.toBeUndefined();
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/latest',
      );
    });

    it('throws TagDeleteError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      try {
        await deleteTag('org', 'repo', 'latest');
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(TagDeleteError);
        expect((err as TagDeleteError).tag).toBe('org/repo:latest');
      }
    });
  });

  describe('expireTag', () => {
    it('expires a tag with correct payload', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await expireTag('org', 'repo', 'v1');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/v1/expire',
        {include_submanifests: true, is_alive: true},
      );
    });

    it('throws TagDeleteError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(expireTag('org', 'repo', 'v1')).rejects.toThrow(
        TagDeleteError,
      );
    });
  });

  describe('bulkDeleteTags', () => {
    it('deletes all tags successfully', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await expect(
        bulkDeleteTags('org', 'repo', ['t1', 't2']),
      ).resolves.toBeUndefined();
    });

    it('uses expireTag when force=true', async () => {
      vi.mocked(axios.post)
        .mockResolvedValueOnce(mockResponse({}))
        .mockResolvedValueOnce(mockResponse({}));

      await bulkDeleteTags('org', 'repo', ['t1', 't2'], true);
      expect(axios.post).toHaveBeenCalledTimes(2);
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain('/expire');
    });

    it('throws BulkOperationError when some deletions fail', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockRejectedValueOnce(new AxiosError('fail'));

      try {
        await bulkDeleteTags('org', 'repo', ['t1', 't2']);
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(BulkOperationError);
        expect(
          (err as BulkOperationError<TagDeleteError>).getErrors().size,
        ).toBe(1);
      }
    });
  });

  describe('getManifestByDigest', () => {
    it('fetches manifest without modelcard by default', async () => {
      const manifest = {
        digest: 'sha256:abc',
        is_manifest_list: false,
        manifest_data: '{}',
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(manifest));

      const result = await getManifestByDigest('org', 'repo', 'sha256:abc');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/manifest/sha256:abc',
      );
      expect(result).toEqual(manifest);
    });

    it('appends include_modelcard query param when true', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({}));

      await getManifestByDigest('org', 'repo', 'sha256:abc', true);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'include_modelcard=true',
      );
    });
  });

  describe('getSecurityDetails', () => {
    it('fetches security details with vulnerabilities', async () => {
      const security = {status: 'scanned', data: {Layer: {}}};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(security));

      const result = await getSecurityDetails('org', 'repo', 'sha256:abc');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/manifest/sha256:abc/security?vulnerabilities=true',
      );
      expect(result).toEqual(security);
    });
  });

  describe('createTag', () => {
    it('creates a tag pointing to a manifest digest', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await createTag('org', 'repo', 'v2', 'sha256:def');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/v2',
        {manifest_digest: 'sha256:def'},
      );
    });
  });

  describe('setExpiration', () => {
    it('sets expiration on a tag', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await setExpiration('org', 'repo', 'v1', 1700000000);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/v1',
        {expiration: 1700000000},
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        setExpiration('org', 'repo', 'v1', 1700000000),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('bulkSetExpiration', () => {
    it('sets expiration for multiple tags', async () => {
      vi.mocked(axios.put)
        .mockResolvedValueOnce(mockResponse({}))
        .mockResolvedValueOnce(mockResponse({}));

      await expect(
        bulkSetExpiration('org', 'repo', ['t1', 't2'], 1700000000),
      ).resolves.toBeUndefined();
    });
  });

  describe('setTagImmutability', () => {
    it('sets immutability on a tag', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await setTagImmutability('org', 'repo', 'v1', true);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/v1',
        {immutable: true},
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        setTagImmutability('org', 'repo', 'v1', true),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('bulkSetTagImmutability', () => {
    it('sets immutability for multiple tags', async () => {
      vi.mocked(axios.put)
        .mockResolvedValueOnce(mockResponse({}))
        .mockResolvedValueOnce(mockResponse({}));

      await expect(
        bulkSetTagImmutability('org', 'repo', ['t1', 't2'], true),
      ).resolves.toBeUndefined();
    });
  });

  describe('restoreTag', () => {
    it('restores a tag to a specific digest', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await restoreTag('org', 'repo', 'v1', 'sha256:abc');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/v1/restore',
        {manifest_digest: 'sha256:abc'},
      );
    });
  });

  describe('permanentlyDeleteTag', () => {
    it('permanently deletes a tag with correct payload', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await permanentlyDeleteTag('org', 'repo', 'v1', 'sha256:abc');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/tag/v1/expire',
        {
          manifest_digest: 'sha256:abc',
          include_submanifests: true,
          is_alive: false,
        },
      );
    });
  });

  describe('getTagPullStatistics', () => {
    it('returns pull statistics on success', async () => {
      const stats = {
        tag_name: 'latest',
        tag_pull_count: 42,
        last_tag_pull_date: '2024-01-01',
        current_manifest_digest: 'sha256:abc',
        manifest_pull_count: 100,
        last_manifest_pull_date: '2024-01-02',
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(stats));

      const result = await getTagPullStatistics('org', 'repo', 'latest');
      expect(result).toEqual(stats);
    });

    it('throws ResourceError with specific message on 404', async () => {
      const err = new AxiosError('Not Found');
      (err as any).response = {status: 404};
      vi.mocked(axios.get).mockRejectedValueOnce(err);

      try {
        await getTagPullStatistics('org', 'repo', 'latest');
        expect.unreachable('should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(ResourceError);
        expect((e as ResourceError).message).toContain('not available');
      }
    });

    it('throws ResourceError with generic message on other errors', async () => {
      const err = new AxiosError('Server Error');
      (err as any).response = {status: 500};
      vi.mocked(axios.get).mockRejectedValueOnce(err);

      try {
        await getTagPullStatistics('org', 'repo', 'latest');
        expect.unreachable('should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(ResourceError);
        expect((e as ResourceError).message).toContain('Unable to fetch');
      }
    });
  });

  describe('TagDeleteError', () => {
    it('stores tag name and error', () => {
      const axiosErr = new AxiosError('fail');
      const err = new TagDeleteError('delete failed', 'org/repo:v1', axiosErr);
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(TagDeleteError);
      expect(err.tag).toBe('org/repo:v1');
      expect(err.error).toBe(axiosErr);
    });
  });
});
