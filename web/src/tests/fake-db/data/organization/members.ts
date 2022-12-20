import {mock} from '../../MockAxios';

const response = {
  members: [
    {
      name: 'bdettelb',
      kind: 'user',
      avatar: {
        name: 'bdettelb',
        hash: 'c18bd4b51f59504fd53f594585d6fe3b',
        color: '#aec7e8',
        kind: 'user',
      },
      teams: [
        {
          name: 'owners',
          avatar: {
            name: 'owners',
            hash: 'b132392a317588e56460e77a8fd74229',
            color: '#1f77b4',
            kind: 'team',
          },
        },
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: [],
    },
    {
      name: 'doconnor',
      kind: 'user',
      avatar: {
        name: 'doconnor',
        hash: '0d035ab57477c5c088fb9b9039e9132c',
        color: '#f7b6d2',
        kind: 'user',
      },
      teams: [
        {
          name: 'owners',
          avatar: {
            name: 'owners',
            hash: 'b132392a317588e56460e77a8fd74229',
            color: '#1f77b4',
            kind: 'team',
          },
        },
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: [],
    },
    {
      name: 'sleesinc',
      kind: 'user',
      avatar: {
        name: 'sleesinc',
        hash: '27a1c473f8acc22c88905cc6cc03faec',
        color: '#ff9896',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: ['python', 'quay-builder-qemu', 'quay-python3'],
    },
    {
      name: 'hdonnay',
      kind: 'user',
      avatar: {
        name: 'hdonnay',
        hash: '84555da1e0d828f02ebb469a3fa07564',
        color: '#2ca02c',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: ['clair', 'clair-fixtures'],
    },
    {
      name: 'jonathankingfc',
      kind: 'user',
      avatar: {
        name: 'jonathankingfc',
        hash: 'fe0274e656bd0a810195fce234f1e17c',
        color: '#e7ba52',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: [],
    },
    {
      name: 'syed',
      kind: 'user',
      avatar: {
        name: 'syed',
        hash: 'd27486c531c5b7ec00bbec3865cea775',
        color: '#17becf',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: ['quay-ui'],
    },
    {
      name: 'harishg',
      kind: 'user',
      avatar: {
        name: 'harishg',
        hash: 'c35afb27219d19dd417c3a2c899eb041',
        color: '#ffbb78',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: ['quay-alpha'],
    },
    {
      name: 'fmissi',
      kind: 'user',
      avatar: {
        name: 'fmissi',
        hash: '98710663edc459a8708c43ba7ca8bae6',
        color: '#9ecae1',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: ['quay-operator-bundle', 'quay-operator-index'],
    },
    {
      name: 'sdadi0',
      kind: 'user',
      avatar: {
        name: 'sdadi0',
        hash: '568337640005bdf306261f49356b6bc6',
        color: '#6b6ecf',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: [],
    },
    {
      name: 'rh-obulatov',
      kind: 'user',
      avatar: {
        name: 'rh-obulatov',
        hash: 'd00e50e3d19d92e6fe75594f1419f696',
        color: '#bcbd22',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: ['quay-ci-app'],
    },
    {
      name: 'bcaton',
      kind: 'user',
      avatar: {
        name: 'bcaton',
        hash: 'bc26239130668309488b9dc4a11b2713',
        color: '#8c6d31',
        kind: 'user',
      },
      teams: [
        {
          name: 'quay',
          avatar: {
            name: 'quay',
            hash: 'a4499c24763a6dea853a657d5c52efab',
            color: '#2ca02c',
            kind: 'team',
          },
        },
      ],
      repositories: [],
    },
  ],
};

const membersPathRegex = new RegExp(`/api/v1/organization/.+/members$`);
mock.onGet(membersPathRegex).reply(() => {
  return [200, response];
});
