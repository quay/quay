import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchOrg,
  fetchOrgsAsSuperUser,
  OrgDeleteError,
  deleteOrg,
  bulkDeleteOrganizations,
  createOrg,
  updateOrgSettings,
  renameOrganization,
  takeOwnership,
} from './OrganizationResource';
import {BulkOperationError} from './ErrorHandling';

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

describe('OrganizationResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchOrg', () => {
    it('fetches organization by name with abort signal', async () => {
      const org = {
        name: 'myorg',
        email: 'org@test.com',
        tag_expiration_s: 1209600,
      };
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(org));

      const result = await fetchOrg('myorg', controller.signal);
      expect(axios.get).toHaveBeenCalledWith('/api/v1/organization/myorg', {
        signal: controller.signal,
      });
      expect(result).toEqual(org);
    });
  });

  describe('fetchOrgsAsSuperUser', () => {
    it('returns organizations array', async () => {
      const orgs = [{name: 'org1'}, {name: 'org2'}];
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({organizations: orgs}),
      );

      const result = await fetchOrgsAsSuperUser();
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/superuser/organizations/',
      );
      expect(result).toEqual(orgs);
    });
  });

  describe('OrgDeleteError', () => {
    it('is an instance of Error with correct properties', () => {
      const axiosErr = new AxiosError('fail');
      const err = new OrgDeleteError('delete failed', 'myorg', axiosErr);
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(OrgDeleteError);
      expect(err.org).toBe('myorg');
      expect(err.error).toBe(axiosErr);
      expect(err.message).toBe('delete failed');
    });
  });

  describe('deleteOrg', () => {
    it('deletes org via standard API', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteOrg('myorg');
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/organization/myorg');
    });

    it('uses superuser API when isSuperUser is true', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteOrg('myorg', true);
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/superuser/organizations/myorg',
      );
    });

    it('throws OrgDeleteError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      try {
        await deleteOrg('myorg');
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(OrgDeleteError);
        expect((err as OrgDeleteError).org).toBe('myorg');
      }
    });
  });

  describe('bulkDeleteOrganizations', () => {
    it('deletes all organizations successfully', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      const result = await bulkDeleteOrganizations(['org1', 'org2']);
      expect(result).toHaveLength(2);
      expect(result[0].status).toBe('fulfilled');
    });

    it('throws BulkOperationError when some deletions fail', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockRejectedValueOnce(new AxiosError('fail'));

      try {
        await bulkDeleteOrganizations(['org1', 'org2']);
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(BulkOperationError);
        expect(
          (err as BulkOperationError<OrgDeleteError>).getErrors().size,
        ).toBe(1);
      }
    });

    it('uses superuser API for bulk delete when isSuperUser is true', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await bulkDeleteOrganizations(['org1', 'org2'], true);
      expect(vi.mocked(axios.delete).mock.calls[0][0]).toContain('superuser');
      expect(vi.mocked(axios.delete).mock.calls[1][0]).toContain('superuser');
    });
  });

  describe('createOrg', () => {
    it('creates org with name only', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createOrg('neworg');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/organization/', {
        name: 'neworg',
      });
    });

    it('creates org with name and email', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createOrg('neworg', 'org@test.com');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/organization/', {
        name: 'neworg',
        email: 'org@test.com',
      });
    });
  });

  describe('updateOrgSettings', () => {
    it('uses organization endpoint for org settings', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateOrgSettings('myorg', {tag_expiration_s: 86400});
      expect(axios.put).toHaveBeenCalledWith('/api/v1/organization/myorg', {
        tag_expiration_s: 86400,
      });
    });

    it('uses user endpoint when isUser is true', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateOrgSettings('myuser', {
        isUser: true,
        tag_expiration_s: 86400,
      });
      expect(vi.mocked(axios.put).mock.calls[0][0]).toBe('/api/v1/user/');
    });

    it('strips null and undefined keys from params', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateOrgSettings('myorg', {
        tag_expiration_s: 86400,
        email: null as unknown as string,
        invoice_email_address: undefined as unknown as string,
      });
      const sentBody = vi.mocked(axios.put).mock.calls[0][1];
      expect(sentBody).not.toHaveProperty('email');
      expect(sentBody).not.toHaveProperty('invoice_email_address');
      expect(sentBody).toHaveProperty('tag_expiration_s', 86400);
    });
  });

  describe('renameOrganization', () => {
    it('renames org via superuser endpoint', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await renameOrganization('oldorg', 'neworg');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/superuser/organizations/oldorg',
        {name: 'neworg'},
      );
    });
  });

  describe('takeOwnership', () => {
    it('takes ownership of a namespace', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await takeOwnership('myns');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/superuser/takeownership/myns',
      );
    });
  });
});
