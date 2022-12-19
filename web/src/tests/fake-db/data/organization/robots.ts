import {mock} from '../../MockAxios';

const response = {
  robots: [
    {
      name: 'projectquay+claircore_github',
      created: 'Mon, 10 May 2021 14:29:36 -0000',
      last_accessed: null,
      teams: [],
      repositories: ['clair', 'golang'],
      description: '',
    },
    {
      name: 'projectquay+clair_github',
      created: 'Thu, 26 Mar 2020 13:46:33 -0000',
      last_accessed: null,
      teams: [],
      repositories: ['clair'],
      description: "Token for clair's Github Actions",
    },
    {
      name: 'projectquay+jzmeskal',
      created: 'Wed, 20 Jan 2021 22:36:49 -0000',
      last_accessed: null,
      teams: [],
      repositories: ['golang'],
      description: 'Robot account for jzmeskal to hack around with.',
    },
    {
      name: 'projectquay+quay_builder_qemu_token',
      created: 'Tue, 01 Mar 2022 20:47:10 -0000',
      last_accessed: null,
      teams: [],
      repositories: ['quay-builder-qemu'],
      description: 'For pushes of quay-builder-qemu image',
    },
    {
      name: 'projectquay+quay_ci_app_github',
      created: 'Tue, 26 Apr 2022 12:46:39 -0000',
      last_accessed: null,
      teams: [],
      repositories: ['quay-ci-app'],
      description: "Token for quay-ci-app's GitHub Actions",
    },
    {
      name: 'projectquay+quay_github',
      created: 'Wed, 07 Apr 2021 21:43:08 -0000',
      last_accessed: null,
      teams: [],
      repositories: [
        'quay',
        'quay-builder',
        'quay-operator',
        'quay-operator-catalog',
        'quay-operator-index',
        'quay-operator-bundle',
        'quay-builder-qemu',
        'quay-ui',
      ],
      description: "Token for quay's Github Actions",
    },
  ],
};

const robotsPathRegex = new RegExp(
  `/api/v1/organization/.+/robots\\?permissions=true&token=false`,
);
mock.onGet(robotsPathRegex).reply(() => {
  return [200, response];
});
