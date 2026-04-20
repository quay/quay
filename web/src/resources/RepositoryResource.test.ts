import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  isNonNormalState,
  fetchAllRepos,
  fetchRepositoriesForNamespace,
  fetchRepositories,
  fetchAllReposAsSuperUser,
  fetchRepositoryDetails,
  createNewRepository,
  setRepositoryVisibility,
  setRepositoryState,
  bulkDeleteRepositories,
  fetchUserRepoPermissions,
  fetchAllTeamPermissionsForRepository,
  setRepoPermissions,
  bulkSetRepoPermissions,
  bulkDeleteRepoPermissions,
  deleteRepoPermissions,
  deleteRepository,
  RepoDeleteError,
  fetchEntityTransitivePermission,
  RepositoryState,
  RepoRole,
  IRepository,
  RepoMember,
} from './RepositoryResource';
import {BulkOperationError, ResourceError} from './ErrorHandling';
import {EntityKind} from './UserResource';

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

/** Creates a minimal IRepository for testing. */
function createMockRepo(
  namespace: string,
  name: string,
  overrides: Partial<IRepository> = {},
): IRepository {
  return {namespace, name, ...overrides};
}

describe('RepositoryResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('isNonNormalState', () => {
    it('returns false for null', () => {
      expect(isNonNormalState(null)).toBe(false);
    });

    it('returns false for undefined', () => {
      expect(isNonNormalState(undefined)).toBe(false);
    });

    it('returns false for NORMAL', () => {
      expect(isNonNormalState('NORMAL')).toBe(false);
    });

    it('returns true for READ_ONLY', () => {
      expect(isNonNormalState('READ_ONLY')).toBe(true);
    });

    it('returns true for MIRROR', () => {
      expect(isNonNormalState('MIRROR')).toBe(true);
    });

    it('returns true for MARKED_FOR_DELETION', () => {
      expect(isNonNormalState('MARKED_FOR_DELETION')).toBe(true);
    });
  });

  describe('fetchRepositoriesForNamespace', () => {
    it('fetches repos for a single namespace', async () => {
      const repos = [createMockRepo('org1', 'repo1')];
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({repositories: repos, next_page: null}),
      );

      const result = await fetchRepositoriesForNamespace('org1');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository?last_modified=true&namespace=org1&public=true',
        {signal: undefined},
      );
      expect(result).toEqual(repos);
    });

    it('recursively paginates when next_page is present', async () => {
      const page1Repos = [createMockRepo('org1', 'repo1')];
      const page2Repos = [createMockRepo('org1', 'repo2')];

      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({repositories: page1Repos, next_page: 'token123'}),
        )
        .mockResolvedValueOnce(
          mockResponse({repositories: page2Repos, next_page: null}),
        );

      const result = await fetchRepositoriesForNamespace('org1');
      expect(result).toEqual([...page1Repos, ...page2Repos]);
      expect(axios.get).toHaveBeenCalledTimes(2);
      expect(vi.mocked(axios.get).mock.calls[1][0]).toContain(
        'next_page=token123',
      );
    });

    it('calls onPartialResult for each page', async () => {
      const page1Repos = [createMockRepo('org1', 'repo1')];
      const page2Repos = [createMockRepo('org1', 'repo2')];
      const onPartialResult = vi.fn();

      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({repositories: page1Repos, next_page: 'tok'}),
        )
        .mockResolvedValueOnce(
          mockResponse({repositories: page2Repos, next_page: null}),
        );

      await fetchRepositoriesForNamespace('org1', {onPartialResult});
      expect(onPartialResult).toHaveBeenCalledTimes(2);
      expect(onPartialResult).toHaveBeenCalledWith(page1Repos);
      expect(onPartialResult).toHaveBeenCalledWith(page2Repos);
    });

    it('passes abort signal to axios', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({repositories: [], next_page: null}),
      );

      await fetchRepositoriesForNamespace('org1', {
        signal: controller.signal,
      });
      expect(vi.mocked(axios.get).mock.calls[0][1]).toEqual({
        signal: controller.signal,
      });
    });
  });

  describe('fetchAllRepos', () => {
    it('returns empty array for empty namespaces', async () => {
      const result = await fetchAllRepos([]);
      expect(result).toEqual([]);
      expect(axios.get).not.toHaveBeenCalled();
    });

    it('returns empty array for null namespaces', async () => {
      const result = await fetchAllRepos(null as unknown as string[]);
      expect(result).toEqual([]);
    });

    it('returns nested arrays by default (not flattened)', async () => {
      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({
            repositories: [createMockRepo('ns1', 'r1')],
            next_page: null,
          }),
        )
        .mockResolvedValueOnce(
          mockResponse({
            repositories: [createMockRepo('ns2', 'r2')],
            next_page: null,
          }),
        );

      const result = await fetchAllRepos(['ns1', 'ns2']);
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual([createMockRepo('ns1', 'r1')]);
      expect(result[1]).toEqual([createMockRepo('ns2', 'r2')]);
    });

    it('flattens results when flatten=true', async () => {
      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({
            repositories: [createMockRepo('ns1', 'r1')],
            next_page: null,
          }),
        )
        .mockResolvedValueOnce(
          mockResponse({
            repositories: [createMockRepo('ns2', 'r2')],
            next_page: null,
          }),
        );

      const result = await fetchAllRepos(['ns1', 'ns2'], {flatten: true});
      expect(result).toEqual([
        createMockRepo('ns1', 'r1'),
        createMockRepo('ns2', 'r2'),
      ]);
    });
  });

  describe('fetchRepositories', () => {
    it('fetches repositories with public=true', async () => {
      const repos = [createMockRepo('org1', 'repo1')];
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({repositories: repos}),
      );

      const result = await fetchRepositories();
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository?last_modified=true&public=true',
      );
      expect(result).toEqual(repos);
    });
  });

  describe('fetchAllReposAsSuperUser', () => {
    it('returns repos with truncated=false for single page', async () => {
      const repos = [createMockRepo('ns', 'r1')];
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({repositories: repos, next_page: null}),
      );

      const result = await fetchAllReposAsSuperUser();
      expect(result).toEqual({repos, truncated: false});
    });

    it('paginates and concatenates results', async () => {
      const page1 = [createMockRepo('ns', 'r1')];
      const page2 = [createMockRepo('ns', 'r2')];

      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({repositories: page1, next_page: 'tok'}),
        )
        .mockResolvedValueOnce(
          mockResponse({repositories: page2, next_page: null}),
        );

      const result = await fetchAllReposAsSuperUser();
      expect(result).toEqual({
        repos: [...page1, ...page2],
        truncated: false,
      });
    });

    it('calls onPartialResult callback for each page', async () => {
      const repos = [createMockRepo('ns', 'r1')];
      const onPartialResult = vi.fn();
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({repositories: repos, next_page: null}),
      );

      await fetchAllReposAsSuperUser({onPartialResult});
      expect(onPartialResult).toHaveBeenCalledWith(repos);
    });
  });

  describe('fetchRepositoryDetails', () => {
    it('fetches repo details with stats', async () => {
      const details = {
        name: 'myrepo',
        namespace: 'myorg',
        can_admin: true,
        can_write: true,
        description: 'test',
        is_public: true,
        is_starred: false,
        is_free_account: false,
        is_organization: true,
        kind: 'image',
        state: 'NORMAL',
        status_token: null,
        tag_expiration_s: 1209600,
        trust_enabled: false,
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(details));

      const result = await fetchRepositoryDetails('myorg', 'myrepo');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/myorg/myrepo?includeStats=true&includeTags=false',
      );
      expect(result).toEqual(details);
    });
  });

  describe('createNewRepository', () => {
    it('creates repository with correct payload', async () => {
      const created = {namespace: 'org', name: 'repo', kind: 'image'};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(created, 201));

      const result = await createNewRepository(
        'org',
        'repo',
        'public',
        'A description',
        'image',
      );
      expect(axios.post).toHaveBeenCalledWith('/api/v1/repository', {
        namespace: 'org',
        repository: 'repo',
        visibility: 'public',
        description: 'A description',
        repo_kind: 'image',
      });
      expect(result).toEqual(created);
    });
  });

  describe('setRepositoryVisibility', () => {
    it('posts visibility change', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({success: true}),
      );

      await setRepositoryVisibility('org', 'repo', 'private');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/changevisibility',
        {visibility: 'private'},
      );
    });
  });

  describe('setRepositoryState', () => {
    it('puts state change', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({success: true}));

      await setRepositoryState('org', 'repo', RepositoryState.READ_ONLY);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/changestate',
        {state: 'READ_ONLY'},
      );
    });
  });

  describe('deleteRepository', () => {
    it('deletes repository successfully', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await expect(deleteRepository('org', 'repo')).resolves.toBeUndefined();
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/repository/org/repo');
    });

    it('throws RepoDeleteError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(
        new AxiosError('Not Found'),
      );

      try {
        await deleteRepository('org', 'repo');
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(RepoDeleteError);
        expect((err as RepoDeleteError).repo).toBe('org/repo');
      }
    });
  });

  describe('bulkDeleteRepositories', () => {
    it('deletes all repositories successfully', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await expect(
        bulkDeleteRepositories([
          createMockRepo('org', 'r1'),
          createMockRepo('org', 'r2'),
        ]),
      ).resolves.toBeUndefined();
    });

    it('throws BulkOperationError when some deletions fail', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockRejectedValueOnce(new AxiosError('fail'));

      try {
        await bulkDeleteRepositories([
          createMockRepo('org', 'r1'),
          createMockRepo('org', 'r2'),
        ]);
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(BulkOperationError);
        expect(
          (err as BulkOperationError<RepoDeleteError>).getErrors().size,
        ).toBe(1);
      }
    });
  });

  describe('fetchUserRepoPermissions', () => {
    it('returns permissions map', async () => {
      const perms = {
        user1: {role: 'admin', name: 'user1', avatar: {}, is_robot: false},
      };
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({permissions: perms}),
      );

      const result = await fetchUserRepoPermissions('org', 'repo');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/user/',
      );
      expect(result).toEqual(perms);
    });
  });

  describe('fetchAllTeamPermissionsForRepository', () => {
    it('returns team permissions map', async () => {
      const perms = {
        team1: {role: 'read', name: 'team1', avatar: {}},
      };
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({permissions: perms}),
      );

      const result = await fetchAllTeamPermissionsForRepository('org', 'repo');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/team/',
      );
      expect(result).toEqual(perms);
    });
  });

  describe('setRepoPermissions', () => {
    it('maps robot entity type to user in the API path', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      const role: RepoMember = {
        org: 'org',
        repo: 'repo',
        name: 'org+bot',
        type: EntityKind.robot,
        role: RepoRole.read,
      };
      await setRepoPermissions(role, RepoRole.write);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/user/org+bot',
        {role: 'write'},
      );
    });

    it('uses team type directly in the API path', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      const role: RepoMember = {
        org: 'org',
        repo: 'repo',
        name: 'devs',
        type: EntityKind.team,
        role: RepoRole.read,
      };
      await setRepoPermissions(role, RepoRole.admin);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/team/devs',
        {role: 'admin'},
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));

      const role: RepoMember = {
        org: 'org',
        repo: 'repo',
        name: 'user1',
        type: EntityKind.user,
        role: RepoRole.read,
      };
      await expect(setRepoPermissions(role, RepoRole.write)).rejects.toThrow(
        ResourceError,
      );
    });
  });

  describe('deleteRepoPermissions', () => {
    it('maps robot type to user in delete path', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      const role: RepoMember = {
        org: 'org',
        repo: 'repo',
        name: 'org+bot',
        type: EntityKind.robot,
        role: RepoRole.read,
      };
      await deleteRepoPermissions(role);
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/user/org+bot',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      const role: RepoMember = {
        org: 'org',
        repo: 'repo',
        name: 'user1',
        type: EntityKind.user,
        role: RepoRole.read,
      };
      await expect(deleteRepoPermissions(role)).rejects.toThrow(ResourceError);
    });
  });

  describe('bulkSetRepoPermissions', () => {
    it('sets permissions for multiple roles', async () => {
      vi.mocked(axios.put)
        .mockResolvedValueOnce(mockResponse({}))
        .mockResolvedValueOnce(mockResponse({}));

      const roles: RepoMember[] = [
        {
          org: 'org',
          repo: 'repo',
          name: 'u1',
          type: EntityKind.user,
          role: RepoRole.read,
        },
        {
          org: 'org',
          repo: 'repo',
          name: 'u2',
          type: EntityKind.user,
          role: RepoRole.read,
        },
      ];
      await expect(
        bulkSetRepoPermissions(roles, RepoRole.write),
      ).resolves.toBeUndefined();
    });
  });

  describe('bulkDeleteRepoPermissions', () => {
    it('deletes permissions for multiple roles', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      const roles: RepoMember[] = [
        {
          org: 'org',
          repo: 'repo',
          name: 'u1',
          type: EntityKind.user,
          role: RepoRole.read,
        },
        {
          org: 'org',
          repo: 'repo',
          name: 'u2',
          type: EntityKind.user,
          role: RepoRole.read,
        },
      ];
      await expect(bulkDeleteRepoPermissions(roles)).resolves.toBeUndefined();
    });
  });

  describe('fetchEntityTransitivePermission', () => {
    it('returns permissions array on success', async () => {
      const permissions = [{role: 'admin'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({permissions}));

      const result = await fetchEntityTransitivePermission(
        'org',
        'repo',
        'user1',
      );
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/permissions/user/user1/transitive',
      );
      expect(result).toEqual(permissions);
    });

    it('returns empty array on 404', async () => {
      const err = new AxiosError('Not Found', '404', undefined, undefined, {
        status: 404,
        data: {},
        statusText: 'Not Found',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });
      vi.mocked(axios.get).mockRejectedValueOnce(err);

      const result = await fetchEntityTransitivePermission(
        'org',
        'repo',
        'user1',
      );
      expect(result).toEqual([]);
    });
  });

  describe('RepoDeleteError', () => {
    it('stores repo name and error', () => {
      const axiosErr = new AxiosError('fail');
      const err = new RepoDeleteError('delete failed', 'org/repo', axiosErr);
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(RepoDeleteError);
      expect(err.repo).toBe('org/repo');
      expect(err.error).toBe(axiosErr);
      expect(err.message).toBe('delete failed');
    });
  });
});
