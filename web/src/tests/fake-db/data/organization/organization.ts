import {mock} from '../../MockAxios';
import {AxiosRequestConfig} from 'axios';

const response = {
  name: 'projectquay',
  email: 'quay-devel+projectquay@redhat.com',
  avatar: {
    name: 'projectquay',
    hash: 'f203c4cdecd4445765750deafa7d589d',
    color: '#17becf',
    kind: 'user',
  },
  is_admin: true,
  is_member: true,
  teams: {
    owners: {
      name: 'owners',
      description: '',
      role: 'admin',
      avatar: {
        name: 'owners',
        hash: 'b132392a317588e56460e77a8fd74229',
        color: '#1f77b4',
        kind: 'team',
      },
      can_view: true,
      repo_count: 0,
      member_count: 2,
      is_synced: false,
    },
    quay: {
      name: 'quay',
      description: 'Quay dev team',
      role: 'admin',
      avatar: {
        name: 'quay',
        hash: 'a4499c24763a6dea853a657d5c52efab',
        color: '#2ca02c',
        kind: 'team',
      },
      can_view: true,
      repo_count: 6,
      member_count: 11,
      is_synced: false,
    },
  },
  ordered_teams: ['owners', 'quay'],
  invoice_email: false,
  invoice_email_address: null,
  tag_expiration_s: 1209600,
  is_free_account: true,
};

const createOrgSuccessResponse = {
  success: true,
};

const orgPathRegex = new RegExp(`/api/v1/organization/(.+)$`);
mock.onGet(orgPathRegex).reply((config) => {
  const orgNameMatch = config.url.match(orgPathRegex);
  if (orgNameMatch && orgNameMatch.length > 1) {
    response.name = orgNameMatch[1];
  }

  return [200, response];
});

mock.onPost('/api/v1/organization/').reply((request: AxiosRequestConfig) => {
  const {name, email} = JSON.parse(request.data);
  return [201, createOrgSuccessResponse];
});

const superUserOrgsResponse = {
  organizations: [
    {
      name: 'superuserorg1',
    },
    {
      name: 'superuserorg2',
    },
  ],
};

mock.onGet(`/api/v1/superuser/organizations/`).reply((config) => {
  return [200, superUserOrgsResponse];
});
