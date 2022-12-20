import {mock} from '../../MockAxios';

const response = {
  robots: [
    {
      name: 'syed+podman',
      created: 'Thu, 04 Nov 2021 16:14:13 -0000',
      last_accessed: null,
      teams: [],
      repositories: ['quay'],
      description: '',
    },
    {
      name: 'syed+test',
      created: 'Wed, 25 Aug 2021 18:47:41 -0000',
      last_accessed: null,
      teams: [],
      repositories: [],
      description: 'test',
    },
  ],
};

const robotsPathRegex = new RegExp(
  `/api/v1/user/robots\\?permissions=true&token=false`,
);
mock.onGet(robotsPathRegex).reply(() => {
  return [200, response];
});
