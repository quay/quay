import {AxiosRequestConfig} from 'axios';
import {mock} from 'src/tests/fake-db/MockAxios';

const response = {
  anonymous: false,
  username: 'user1',
  avatar: {
    name: 'user1',
    hash: 'd27382531c5b7ec00bbec3865cea775',
    color: '#17becf',
    kind: 'user',
  },
  can_create_repo: true,
  is_me: true,
  verified: true,
  email: 'user1@redhat.com',
  logins: [
    {
      service: 'rhsso',
      service_identifier:
        'f:9f97392e-a27f-4e15-91ae-81da814b530f:user1@redhat.com',
      metadata: {
        service_username: 'user1',
      },
    },
  ],
  invoice_email: false,
  invoice_email_address: null,
  preferred_namespace: false,
  tag_expiration_s: 1209600,
  prompts: [],
  super_user: false,
  company: '',
  family_name: null,
  given_name: null,
  location: null,
  is_free_account: true,
  has_password_set: true,
  organizations: [
    {
      name: 'quay',
      avatar: {
        name: 'quay',
        hash: '641eefcb35fec8d5622b495879a91653',
        color: '#2ca02c',
        kind: 'org',
      },
      can_create_repo: true,
      public: false,
      is_org_admin: true,
      preferred_namespace: true,
    },
    {
      name: 'projectquay',
      avatar: {
        name: 'projectquay',
        hash: 'f203c4cdecd4445765750deafa7d589d',
        color: '#17becf',
        kind: 'org',
      },
      can_create_repo: true,
      public: false,
      is_org_admin: true,
      preferred_namespace: false,
    },
    {
      name: 'testorg',
      avatar: {
        name: 'testorg',
        hash: '80d7b15766626006f56d6dbbcb831767',
        color: '#969696',
        kind: 'org',
      },
      can_create_repo: true,
      public: false,
      is_org_admin: true,
      preferred_namespace: false,
    },
  ],
};

mock.onGet('/api/v1/user/').reply((request: AxiosRequestConfig) => {
  return [200, response];
});

const superUserUsersResponse = {
  users: [
    {
      username: 'syed',
    },
    {
      username: 'dconnor',
    },
    {
      username: 'jonathankingfc',
    },
    {
      username: 'bcaton',
    },
  ],
};

mock.onGet('/api/v1/superuser/users/').reply((request: AxiosRequestConfig) => {
  return [200, superUserUsersResponse];
});
