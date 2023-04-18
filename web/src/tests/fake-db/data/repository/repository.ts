import {AxiosRequestConfig} from 'axios';
import {IRepository} from 'src/resources/RepositoryResource';
import {mock} from 'src/tests/fake-db/MockAxios';

const responses = {
  user1: {
    repositories: [
      {
        namespace: 'user1',
        name: 'postgres',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656432090,
        popularity: 0.0,
        is_starred: false,
      },
      {
        namespace: 'user1',
        name: 'nested/repository',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656432090,
        popularity: 0.0,
        is_starred: false,
      },
    ],
  },
  quay: {
    repositories: [
      {
        namespace: 'quay',
        name: 'postgres',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656428008,
        popularity: 0.0,
        is_starred: false,
      },
      {
        namespace: 'quay',
        name: 'python',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656428008,
        popularity: 0.0,
        is_starred: false,
      },
      {
        namespace: 'quay',
        name: 'clair',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656428008,
        popularity: 0.0,
        is_starred: false,
      },
      {
        namespace: 'quay',
        name: 'redis',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656428008,
        popularity: 0.0,
        is_starred: false,
      },
      {
        namespace: 'quay',
        name: 'ansible',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656428008,
        popularity: 0.0,
        is_starred: false,
      },
      {
        namespace: 'quay',
        name: 'busybox',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656428008,
        popularity: 0.0,
        is_starred: false,
      },
    ],
  },
  projectquay: {
    repositories: [],
  },
  testorg: {
    repositories: [
      {
        namespace: 'testorg',
        name: 'redis',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 0,
          configured_quota: 104857600,
        },
        last_modified: null,
        popularity: 1.0,
        is_starred: false,
      },
      {
        namespace: 'testorg',
        name: 'postgres',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656426723,
        popularity: 1.0,
        is_starred: false,
      },
    ],
  },
};

const response = {
  namespace: 'quay',
  name: 'testrepo',
  kind: 'image',
};

const successResponse = {
  success: true,
};

const repoDetailsResponse = {
  state: 'NORMAL',
};

mock
  .onGet('/api/v1/repository?last_modified=true&namespace=quay&public=true')
  .reply(200, responses.quay);
mock
  .onGet(
    '/api/v1/repository?last_modified=true&namespace=projectquay&public=true',
  )
  .reply(200, responses.projectquay);
mock
  .onGet('/api/v1/repository?last_modified=true&namespace=testorg&public=true')
  .reply(200, responses.testorg);
mock
  .onGet('/api/v1/repository?last_modified=true&namespace=user1&public=true')
  .reply(200, responses.user1);
mock
  .onGet('/api/v1/repository?last_modified=true&namespace=&public=true')
  .reply(200, {repositories: []});
mock
  .onGet(
    '/api/v1/repository?last_modified=true&namespace=manyrepositories&public=true',
  )
  .reply((request: AxiosRequestConfig) => {
    const repos = [];
    for (let i = 0; i < 50; i++) {
      const repo: IRepository = {
        namespace: 'manyrepositories',
        name: '',
        description: null,
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656432090,
        popularity: 0.0,
        is_starred: false,
      };
      repo.name = `repo${i}`;
      repos.push(repo);
    }
    return [200, {repositories: repos}];
  });

const repoDetailsPathRegex = new RegExp(
  `/api/v1/repository/.+/.+?includeStats=false&includeTags=false`,
);
mock.onGet(repoDetailsPathRegex).reply(200, repoDetailsResponse);

mock.onPost('/api/v1/repository').reply((request: AxiosRequestConfig) => {
  const {namespace, repository, visibility, description, repo_kind} =
    JSON.parse(request.data);
  responses[namespace].repositories.push({
    namespace: namespace,
    name: repository,
    description: description,
    is_public: visibility == 'public',
    kind: repo_kind,
    state: 'NORMAL',
    quota_report: {
      quota_bytes: 132459661,
      configured_quota: 104857600,
    },
    last_modified: 1656426723,
    popularity: 1.0,
    is_starred: false,
  });
  return [201, successResponse];
});

const visibilityPathRegex = new RegExp(
  `/api/v1/repository/.+/.+/changevisibility`,
);
mock.onPost(visibilityPathRegex).reply((request: AxiosRequestConfig) => {
  const {visibility} = JSON.parse(request.data);
  const splitUrl = request.url.split('/');
  const org = splitUrl[4];
  const requestedRepo = splitUrl.slice(5, splitUrl.length - 1).join('/');
  console.log('org', org);
  console.log('request.url', request.url);
  console.log('requestedRepo', requestedRepo);

  const repoIndex = responses[org].repositories.findIndex(
    (repo) => repo.name === requestedRepo,
  );
  responses[org].repositories[repoIndex].is_public = visibility === 'public';
  return [200, successResponse];
});

const deleteRepoRegex = new RegExp(`/api/v1/repository/.+/.+`);
mock.onDelete(deleteRepoRegex).reply((request: AxiosRequestConfig) => {
  const splitUrl = request.url.split('/');
  const org = splitUrl[4];
  const requestedRepo = splitUrl.slice(5, splitUrl.length).join('/');
  responses[org].repositories = responses[org].repositories.filter(
    (repo) => repo.name !== requestedRepo,
  );
  return [204, successResponse];
});
