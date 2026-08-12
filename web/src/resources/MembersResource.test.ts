import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchAllMembers,
  fetchMembersForOrg,
  fetchCollaboratorsForOrg,
  fetchTeamMembersForOrg,
  deleteTeamMemberForOrg,
  deleteCollaboratorForOrg,
  addMemberToTeamForOrg,
} from './MembersResource';

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

describe('MembersResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchMembersForOrg', () => {
    it('fetches members for an org', async () => {
      const controller = new AbortController();
      const members = [{name: 'alice', kind: 'user'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({members}));

      const result = await fetchMembersForOrg('myorg', controller.signal);
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/members',
        {signal: controller.signal},
      );
      expect(result).toEqual(members);
    });
  });

  describe('fetchCollaboratorsForOrg', () => {
    it('fetches collaborators for an org', async () => {
      const controller = new AbortController();
      const collaborators = [{name: 'bob', kind: 'user'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({collaborators}));

      const result = await fetchCollaboratorsForOrg('myorg', controller.signal);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain('collaborators');
      expect(result).toEqual(collaborators);
    });
  });

  describe('fetchAllMembers', () => {
    it('fetches members for multiple orgs in parallel', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get)
        .mockResolvedValueOnce(mockResponse({members: [{name: 'a'}]}))
        .mockResolvedValueOnce(mockResponse({members: [{name: 'b'}]}));

      const result = await fetchAllMembers(['org1', 'org2'], controller.signal);
      expect(result).toHaveLength(2);
    });
  });

  describe('fetchTeamMembersForOrg', () => {
    it('fetches team members with includePending', async () => {
      const teamMembers = {members: [{name: 'alice'}]};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(teamMembers));

      const result = await fetchTeamMembersForOrg('myorg', 'devs');
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'includePending=true',
      );
      expect(result).toEqual(teamMembers);
    });
  });

  describe('deleteTeamMemberForOrg', () => {
    it('deletes a team member', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteTeamMemberForOrg('myorg', 'devs', 'alice');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/team/devs/members/alice',
      );
    });
  });

  describe('deleteCollaboratorForOrg', () => {
    it('deletes a collaborator', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteCollaboratorForOrg('myorg', 'bob');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/members/bob',
      );
    });
  });

  describe('addMemberToTeamForOrg', () => {
    it('adds a member to a team', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({added: true}));

      const result = await addMemberToTeamForOrg('myorg', 'devs', 'alice');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/team/devs/members/alice',
        {},
      );
      expect(result).toEqual({added: true});
    });
  });
});
