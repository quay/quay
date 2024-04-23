/// <reference types="cypress" />

import moment from 'moment';
import {formatDate, humanizeTimeForExpiry} from '../../src/libs/utils';
import {
  getBuildMessage,
  getCompletedBuildPhases,
} from '../../src/routes/Build/Utils';

const buildData = [
  {
    id: 'build001',
    status: 'error',
    trigger: {
      message: 'Triggered by commit commit1',
    },
    started: 'Tue, 28 Nov 2023 15:37:33 -0000',
    tags: ['commit1'],
  },
  {
    id: 'build002',
    status: 'internal error',
    trigger: {
      message: 'user1',
    },
    started: 'Mon, 27 Nov 2023 20:21:19 -0000',
    tags: ['latest'],
  },
  {
    id: 'build003',
    status: 'build-scheduled',
    trigger: {
      message: '(Manually Triggered Build)',
    },
    started: 'Mon, 27 Nov 2023 20:21:19 -0000',
    tags: ['latest'],
  },
  {
    id: 'build004',
    status: 'unpacking',
    trigger: {
      message: 'Triggered by push to repository https://github.com/quay/quay',
    },
    started: 'Sun, 12 Nov 2023 16:24:50 -0000',
    tags: [],
  },
  {
    id: 'build005',
    status: 'pulling',
    trigger: {
      message:
        'Triggered by push to GitHub repository https://github.com/quay/quay',
    },
    started: 'Sun, 12 Nov 2023 16:24:50 -0000',
    tags: [],
  },
  {
    id: 'build006',
    status: 'building',
    trigger: {
      message:
        'Triggered by push to BitBucket repository https://github.com/quay/quay',
    },
    started: 'Sun, 12 Nov 2023 16:24:50 -0000',
    tags: [],
  },
  {
    id: 'build007',
    status: 'pushing',
    trigger: {
      message:
        'Triggered by push to GitLab repository https://github.com/quay/quay',
    },
    started: 'Sun, 12 Nov 2023 16:24:50 -0000',
    tags: [],
  },
  {
    id: 'build008',
    status: 'waiting',
    trigger: {
      message: 'custom-git build from branch',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'master',
      refLink: '',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build009',
    status: 'complete',
    trigger: {
      message: 'github build from branch',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'master',
      refLink: 'https://github.com/quay/quay/tree/master',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build010',
    status: 'cancelled',
    trigger: {
      message: 'gitlab build from branch',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'master',
      refLink: 'https://github.com/quay/quay/tree/master',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build011',
    status: 'expired',
    trigger: {
      message: 'bitbucket build from branch',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'master',
      refLink: 'https://github.com/quay/quay/branch/master',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build012',
    status: 'waiting',
    trigger: {
      message: 'custom git build from tag',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'newtag',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build013',
    status: 'waiting',
    trigger: {
      message: 'github build from tag',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'newtag',
      refLink: 'https://github.com/quay/quay/releases/tag/newtag',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build014',
    status: 'waiting',
    trigger: {
      message: 'gitlab build from tag',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'newtag',
      refLink: 'https://github.com/quay/quay/commits/newtag',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build015',
    status: 'waiting',
    trigger: {
      message: 'bitbucket build from tag',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'newtag',
      refLink: 'https://github.com/quay/quay/commits/tag/newtag',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
  {
    id: 'build016',
    status: 'waiting',
    trigger: {
      message:
        'random text to test long description, random text to test long description, ran',
      messageLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      authoredDate: '2023-11-28T10:42:17-05:00',
      author: 'user1',
      commit: 'commit2',
      commitLink:
        'https://github.com/quay/quay/commit/commit2b46cf9a7510fd9ef3bcc7191834c5abda',
      ref: 'newtag',
      refLink: 'https://github.com/quay/quay/commits/tag/newtag',
    },
    started: 'Thu, 28 Sep 2023 16:52:29 -0000',
    tags: ['latest', 'master'],
  },
];

describe('Repository Builds', () => {
  beforeEach(() => {
    cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as('getUser');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
      'getCsrfToken',
    );
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo?includeStats=false&includeTags=false',
      {fixture: 'testrepo.json'},
    ).as('getRepo');
    cy.intercept('GET', '/api/v1/organization/testorg', {
      fixture: 'testorg.json',
    }).as('getOrg');
  });

  it('Tab does not appear if repo is mirror', () => {
    cy.fixture('testrepo.json').then((repoFixture) => {
      repoFixture.state = 'MIRROR';
      cy.intercept(
        'GET',
        '/api/v1/repository/testorg/testrepo?includeStats=false&includeTags=false',
        repoFixture,
      ).as('getRepo');
    });
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/tag/?limit=100&page=1&onlyActiveTags=true',
      {
        page: 1,
        has_additional: false,
        tags: [],
      },
    ).as('getTag');
    cy.visit('/repository/testorg/testrepo');
    cy.contains('Builds').should('not.exist');
  });

  it('Tab does not appear if repo is readonly', () => {
    cy.fixture('testrepo.json').then((repoFixture) => {
      repoFixture.state = 'READONLY';
      cy.intercept(
        'GET',
        '/api/v1/repository/testorg/testrepo?includeStats=false&includeTags=false',
        repoFixture,
      ).as('getRepo');
    });
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/tag/?limit=100&page=1&onlyActiveTags=true',
      {
        page: 1,
        has_additional: false,
        tags: [],
      },
    ).as('getTag');
    cy.visit('/repository/testorg/testrepo');
    cy.contains('Builds').should('not.exist');
  });

  it('Shows empty list', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      builds: [],
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains('Build History');
    cy.contains(
      'No matching builds found. Please start a new build or adjust filter to view build status.',
    );
  });

  it('Displays build status', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    for (const expectedData of buildData) {
      cy.contains('tr', expectedData.id).within(() => {
        cy.get('td[data-label="Status"]').contains(expectedData.status);
        cy.get('td[data-label="Triggered by"]').within(() => {
          const messageElement = cy.contains(expectedData.trigger.message);
          if (expectedData.trigger.messageLink) {
            messageElement.should(
              'have.attr',
              'href',
              expectedData.trigger.messageLink,
            );
          }
          if (expectedData.trigger.authoredDate) {
            // Time difference between now and author date in seconds
            const authorDate =
              (new Date().getTime() -
                new Date(expectedData.trigger.authoredDate).getTime()) /
              1000;
            cy.contains(humanizeTimeForExpiry(authorDate));
          }
          if (expectedData.trigger.author) {
            cy.contains(expectedData.trigger.author);
          }
          if (expectedData.trigger.commit) {
            const commitElement = cy.contains(expectedData.trigger.commit);
            if (expectedData.trigger.commitLink) {
              commitElement.should(
                'have.attr',
                'href',
                expectedData.trigger.commitLink,
              );
            }
          }
          if (expectedData.trigger.ref) {
            const refElement = cy.contains(expectedData.trigger.ref);
            if (expectedData.trigger.refLink) {
              refElement.should(
                'have.attr',
                'href',
                expectedData.trigger.refLink,
              );
            }
          }
        });
        cy.get('td[data-label="Date started"]').contains(
          formatDate(expectedData.started),
        );
        for (const tag of expectedData.tags) {
          cy.get('td[data-label="Tags"]').contains(tag);
        }
      });
    }
  });

  it('Expands long commit messages', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains('tr', 'random text to test long description').within(() => {
      cy.contains('success viewing long description').should('not.exist');
      cy.get('[data-testid="expand-long-description"]').click();
      cy.contains('success viewing long description');
    });
  });

  it('Filters by 48 hours', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/build/?limit=100&since=*',
      {fixture: 'builds.json'},
    ).as('getBuilds48Hours');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains('Last 48 hours').click();
    cy.wait('@getBuilds48Hours').then(({request}) => {
      const start = moment((request.query.since as number) * 1000);
      const end = moment(new Date());
      const days = Math.round(moment.duration(end.diff(start)).asDays());
      expect(days).equal(2);
    });
  });

  it('Filters by 30 days', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/build/?limit=100&since=*',
      {fixture: 'builds.json'},
    ).as('getBuilds30Days');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains('Last 30 days').click();
    cy.wait('@getBuilds30Days').then(({request}) => {
      const start = moment((request.query.since as number) * 1000);
      const end = moment(new Date());
      const days = Math.round(moment.duration(end.diff(start)).asDays());
      expect(days).equal(30);
    });
  });

  it('displays build triggers', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    const expectedRowData = [
      {
        name: 'push to GitHub repository testgitorg/testgitrepo',
        dockerfilePath: '/Dockerfile',
        context: '/',
        branchtagRegex: '^newbranch$',
        robot: '(None)',
        taggingOptions: [
          'Branch/tag name',
          'latest if default branch',
          '${commit_info.short_sha}',
        ],
      },
      {
        name: 'push to repository https://github.com/testgitorg/testgitrepo',
        dockerfilePath: '/Dockerfile',
        context: '/web',
        branchtagRegex: 'All',
        robot: '(None)',
        taggingOptions: ['Branch/tag name', '${commit_info.short_sha}'],
      },
      {
        name: 'push to GitLab repository testgitorg/testgitrepo',
        dockerfilePath: '/application/Dockerfile',
        context: '/',
        branchtagRegex: 'All',
        robot: '(None)',
        taggingOptions: [],
      },
    ];
    for (const expectedData of expectedRowData) {
      cy.contains('tr', expectedData.name).within(() => {
        cy.get('td[data-label="trigger name"]').contains(expectedData.name);
        cy.get('td[data-label="dockerfile path"]').contains(
          expectedData.dockerfilePath,
        );
        cy.get('td[data-label="context"]').contains(expectedData.context);
        cy.get('td[data-label="branchtag regex"]').contains(
          expectedData.branchtagRegex,
        );
        cy.get('td[data-label="pull robot"]').contains(expectedData.robot);
        for (const option of expectedData.taggingOptions) {
          cy.get('td[data-label="tagging options"]').contains(option);
        }
      });
    }
  });

  it('Disables trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'PUT',
      '/api/v1/repository/testorg/testrepo/trigger/githubfe-70b5-4bf9-8eb9-8dccf9874aed',
      {
        statusCode: 200,
      },
    ).as('disableTrigger');

    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains(
      'tr',
      'push to GitHub repository testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('Disable Trigger').click();
    });
    cy.contains('Disable Build Trigger');
    cy.contains('Are you sure you want to disable this build trigger?');
    cy.contains('button', 'Disable Build Trigger').click();
    cy.get('@disableTrigger')
      .its('request.body')
      .should('deep.equal', {enabled: false});
    cy.contains('Successfully disabled trigger');
  });

  it('Enables trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'PUT',
      '/api/v1/repository/testorg/testrepo/trigger/disabled-9fd5-4005-bc95-d3156855f0d5',
      {
        statusCode: 200,
      },
    ).as('enableTrigger');

    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains(
      'tr',
      'push to GitLab repository testgitorg/disabledrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('Enable Trigger').click();
    });
    cy.contains('Enable Build Trigger');
    cy.contains('Are you sure you want to enable this build trigger?');
    cy.contains('button', 'Enable Build Trigger').click();
    cy.get('@enableTrigger')
      .its('request.body')
      .should('deep.equal', {enabled: true});
    cy.contains('Successfully enabled trigger');
  });

  it('Views trigger credentials', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    // Viewing github credentials
    cy.contains(
      'tr',
      'push to GitHub repository testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('View Credentials').click();
    });
    cy.contains('Trigger Credentials');
    cy.contains(
      'The following key has been automatically added to your source control repository.',
    );
    cy.get('[data-testid="SSH Public Key"').within(() => {
      cy.get('input').should('have.value', 'fakekey');
    });
    cy.contains('Done').click();

    // Viewing git credentials
    cy.contains(
      'tr',
      'push to repository https://github.com/testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('View Credentials').click();
    });
    cy.contains('Trigger Credentials');
    cy.contains(
      'In order to use this trigger, the following first requires action:',
    );
    cy.contains(
      'You must give the following public key read access to the git repository.',
    );
    cy.contains(
      'You must set your repository to POST to the following URL to trigger a build.',
    );
    cy.contains(
      'For more information, refer to the Custom Git Triggers documentation.',
    );
    cy.get('[data-testid="SSH Public Key"').within(() => {
      cy.get('input').should('have.value', 'fakekey');
    });
    cy.get('[data-testid="Webhook Endpoint URL"').within(() => {
      cy.get('input').should(
        'have.value',
        `https://$token:faketoken@${Cypress.env(
          'REACT_QUAY_APP_API_URL',
        ).replace(
          'http://',
          '',
        )}/webhooks/push/trigger/67595ac0-5014-4962-81a0-9a8d336ca851`,
      );
    });
    cy.contains('Done').click();

    // Viewing gitlab credentials
    cy.contains(
      'tr',
      'push to GitLab repository testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('View Credentials').click();
    });
    cy.contains('Trigger Credentials');
    cy.contains(
      'The following key has been automatically added to your source control repository.',
    );
    cy.get('[data-testid="SSH Public Key"').within(() => {
      cy.get('input').should('have.value', 'fakekey');
    });
  });

  it('Delete trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'DELETE',
      '/api/v1/repository/testorg/testrepo/trigger/githubfe-70b5-4bf9-8eb9-8dccf9874aed',
      {
        statusCode: 200,
      },
    ).as('deleteTrigger');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.contains(
      'tr',
      'push to GitHub repository testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('Delete Trigger').click();
    });
    cy.contains('Delete Build Trigger');
    cy.contains(
      'Are you sure you want to delete this build trigger? No further builds will be automatically started.',
    );
    cy.contains('button', 'Delete Trigger').click();
    cy.wait('@deleteTrigger');
    cy.contains('Successfully deleted trigger');
  });

  it('Re-enable disabled trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.fixture('build-triggers.json').then((triggersFixture) => {
      const githubTrigger = triggersFixture.triggers.filter(
        (trigger) => trigger.id === 'githubfe-70b5-4bf9-8eb9-8dccf9874aed',
      )[0];
      const gitTrigger = triggersFixture.triggers.filter(
        (trigger) => trigger.id === 'custom-git35014-4962-81a0-9a8d336ca851',
      )[0];
      const gitlabTrigger = triggersFixture.triggers.filter(
        (trigger) => trigger.id === 'gitlab82-9fd5-4005-bc95-d3156855f0d5',
      )[0];
      githubTrigger.enabled = false;
      githubTrigger.disabled_reason = 'user_toggled';
      gitTrigger.enabled = false;
      gitTrigger.disabled_reason = 'successive_build_failures';
      gitlabTrigger.enabled = false;
      gitlabTrigger.disabled_reason = 'successive_build_internal_errors';
      cy.intercept(
        'GET',
        '/api/v1/repository/testorg/testrepo/trigger/',
        triggersFixture,
      ).as('getBuildTriggers');
    });
    cy.intercept(
      'PUT',
      '/api/v1/repository/testorg/testrepo/trigger/githubfe-70b5-4bf9-8eb9-8dccf9874aed',
      {
        statusCode: 200,
      },
    ).as('enableGithubTrigger');
    cy.intercept(
      'PUT',
      '/api/v1/repository/testorg/testrepo/trigger/custom-git35014-4962-81a0-9a8d336ca851',
      {
        statusCode: 200,
      },
    ).as('enableGitTrigger');
    cy.intercept(
      'PUT',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab82-9fd5-4005-bc95-d3156855f0d5',
      {
        statusCode: 200,
      },
    ).as('enableGitlabTrigger');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains(
      'tbody',
      'push to GitHub repository testgitorg/testgitrepo',
    ).within(() => {
      cy.contains('This build trigger is user disabled and will not build.');
      cy.contains('Re-enable this trigger').click();
    });
    cy.contains('Are you sure you want to enable this build trigger?');
    cy.contains('button', 'Enable Build Trigger').click();
    cy.wait('@enableGithubTrigger')
      .its('request.body')
      .should('deep.equal', {enabled: true});
    cy.contains(
      'tbody',
      'push to repository https://github.com/testgitorg/testgitrepo',
    ).within(() => {
      cy.contains(
        'This build trigger was automatically disabled due to successive failures.',
      );
      cy.contains('Re-enable this trigger').click();
    });
    cy.contains('Are you sure you want to enable this build trigger?');
    cy.contains('button', 'Enable Build Trigger').click();
    cy.wait('@enableGitTrigger')
      .its('request.body')
      .should('deep.equal', {enabled: true});
    cy.contains(
      'tbody',
      'push to GitLab repository testgitorg/testgitrepo',
    ).within(() => {
      cy.contains(
        'This build trigger was automatically disabled due to successive internal errors.',
      );
      cy.contains('Re-enable this trigger').click();
    });
    cy.contains('Are you sure you want to enable this build trigger?');
    cy.contains('button', 'Enable Build Trigger').click();
    cy.wait('@enableGitlabTrigger')
      .its('request.body')
      .should('deep.equal', {enabled: true});
  });

  it('Provides option to delete incomplete trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.fixture('build-triggers.json').then((triggersFixture) => {
      const githubTrigger = triggersFixture.triggers.filter(
        (trigger) => trigger.id === 'githubfe-70b5-4bf9-8eb9-8dccf9874aed',
      )[0];
      githubTrigger.is_active = false;
      cy.intercept(
        'GET',
        '/api/v1/repository/testorg/testrepo/trigger/',
        triggersFixture,
      ).as('getBuildTriggers');
    });
    cy.intercept(
      'DELETE',
      '/api/v1/repository/testorg/testrepo/trigger/githubfe-70b5-4bf9-8eb9-8dccf9874aed',
      {
        statusCode: 200,
      },
    ).as('deleteTrigger');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains('This build trigger has not had its setup completed.');
    cy.contains('Delete Trigger').click();
    cy.wait('@deleteTrigger');
  });

  it('manually runs github trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/githubfe-70b5-4bf9-8eb9-8dccf9874aed/fields/refs',
      {fixture: 'build-trigger-refs.json'},
    ).as('getBuildTriggerRefs');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/githubfe-70b5-4bf9-8eb9-8dccf9874aed/start',
      {statusCode: 200, body: {id: 'build001'}},
    ).as('startBuild');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    const submitBuild = (cy) => {
      cy.get('#manually-start-build-modal').within(() => {
        cy.contains('button', 'Start Build').should('be.disabled');
        cy.contains('Manually Start Build Trigger');
        cy.contains('push to GitHub repository testgitorg/testgitrepo');
        cy.contains('Branch/Tag:');
        cy.get('button[aria-label="Menu toggle"]').click();
        cy.contains('master');
        cy.contains('development');
        cy.contains('1.0.0');
        cy.contains('1.0.1').click();
        cy.contains('button', 'Start Build').click();
        cy.get('@startBuild')
          .its('request.body')
          .should('deep.equal', {refs: {kind: 'tag', name: '1.0.1'}});
      });
      cy.contains('Build started successfully with ID build001');
    };

    // Test with build history button
    cy.contains('Start New Build').click();
    cy.get('#start-build-modal').within(() => {
      cy.contains(
        'tr',
        'push to GitHub repository testgitorg/testgitrepo',
      ).within(() => {
        cy.contains('^newbranch$');
        cy.contains('Run Trigger Now').click();
      });
    });
    submitBuild(cy);

    // Test run within row
    cy.contains(
      'tr',
      'push to GitHub repository testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('Run Trigger').click();
    });
    submitBuild(cy);
  });

  it('manually runs gitlab trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab82-9fd5-4005-bc95-d3156855f0d5/fields/refs',
      {fixture: 'build-trigger-refs.json'},
    ).as('getBuildTriggerRefs');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab82-9fd5-4005-bc95-d3156855f0d5/start',
      {statusCode: 200, body: {id: 'build001'}},
    ).as('startBuild');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    const submitBuild = (cy) => {
      cy.get('#manually-start-build-modal').within(() => {
        cy.contains('button', 'Start Build').should('be.disabled');
        cy.contains('Manually Start Build Trigger');
        cy.contains('push to GitLab repository testgitorg/testgitrepo');
        cy.contains('Branch/Tag:');
        cy.get('button[aria-label="Menu toggle"]').click();
        cy.contains('master');
        cy.contains('development');
        cy.contains('1.0.0');
        cy.contains('1.0.1').click();
        cy.contains('button', 'Start Build').click();
        cy.get('@startBuild')
          .its('request.body')
          .should('deep.equal', {refs: {kind: 'tag', name: '1.0.1'}});
      });
      cy.contains('Build started successfully with ID build001');
    };

    // Test with build history button
    cy.contains('Start New Build').click();
    cy.get('#start-build-modal').within(() => {
      cy.contains(
        'tr',
        'push to GitLab repository testgitorg/testgitrepo',
      ).within(() => {
        cy.contains('All');
        cy.contains('Run Trigger Now').click();
      });
    });
    submitBuild(cy);

    // Test run within row
    cy.contains(
      'tr',
      'push to GitLab repository testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('Run Trigger').click();
    });
    submitBuild(cy);
  });

  it('manually runs custom trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/custom-git35014-4962-81a0-9a8d336ca851/start',
      {statusCode: 200, body: {id: 'build001'}},
    ).as('startBuild');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    const submitBuild = (cy) => {
      cy.get('#manually-start-build-modal').within(() => {
        cy.contains('button', 'Start Build').should('be.disabled');
        cy.contains('Manually Start Build Trigger');
        cy.contains(
          'push to repository https://github.com/testgitorg/testgitrepo',
        );
        cy.contains('Commit:');
        cy.get('#manual-build-commit-input').type('invalidcommit');
        cy.contains('Invalid commit pattern');
        cy.get('#manual-build-commit-input').clear();
        cy.get('#manual-build-commit-input').type(
          'adadadf141dd4141a4ecbb3cb21282053a678203',
        );
        cy.contains('button', 'Start Build').click();
        cy.get('@startBuild').its('request.body').should('deep.equal', {
          commit_sha: 'adadadf141dd4141a4ecbb3cb21282053a678203',
        });
      });
      cy.contains('Build started successfully with ID build001');
    };

    // Test with build history button
    cy.contains('Start New Build').click();
    cy.get('#start-build-modal').within(() => {
      cy.contains(
        'tr',
        'push to repository https://github.com/testgitorg/testgitrepo',
      ).within(() => {
        cy.contains('All');
        cy.contains('Run Trigger Now').click();
      });
    });
    submitBuild(cy);

    // Test run within row
    cy.contains(
      'tr',
      'push to repository https://github.com/testgitorg/testgitrepo',
    ).within(() => {
      cy.get('button[data-testid="build-trigger-actions-kebab"]').click();
      cy.contains('Run Trigger').click();
    });
    submitBuild(cy);
  });

  it('runs trigger with dockerfile', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/privaterepo?includeStats=false&includeTags=false',
      {statusCode: 200, body: {is_public: false}},
    ).as('getRepoDetails');
    cy.intercept(
      'GET',
      '/api/v1/organization/testorg/robots?permissions=true&token=false',
      {fixture: 'robots.json'},
    ).as('getRobots');
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/permissions/user/testorg+testrobot/transitive',
      {statusCode: 200, body: {permissions: [{role: 'read'}]}},
    ).as('getTransitivePermissions');
    cy.intercept('POST', '/api/v1/filedrop/', {
      statusCode: 200,
      body: {
        url: `${Cypress.env(
          'REACT_QUAY_APP_API_URL',
        )}/userfiles/a1599e3f-aa56-4f90-8b1a-ec5f9e63ffe7`,
        file_id: 'a1599e3f-aa56-4f90-8b1a-ec5f9e63ffe7',
      },
    }).as('getFileDrop');
    cy.intercept('POST', '/api/v1/repository/testorg/testrepo/build/', {
      statusCode: 201,
      body: {id: 'build001'},
    }).as('startBuild');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.contains('Start New Build').click();
    cy.get('#start-build-modal').within(() => {
      cy.contains('Upload Dockerfile').click();
      cy.fixture('TestDockerfile', null).as('dockerfile');
      cy.get('#dockerfile-upload').selectFile('@dockerfile', {
        action: 'drag-drop',
      });
      cy.contains(
        'The selected Dockerfile contains a FROM that refers to private repository testorg/privaterepo.',
      );
      cy.contains(
        'A robot account with read access to that repository is required for the build:',
      );
      cy.get('#repository-creator-dropdown').click();
      cy.contains('testorg+testrobot2');
      cy.contains('testorg+testrobot').click();
      cy.contains('button', 'Start Build').click();
    });
    cy.contains('Build started with ID build001');
  });
});

describe('Repository Builds - Create Custom Git Build Triggers', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Creates build trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuilds');
    cy.visit('/repository/testorg/testrepo?tab=builds');
    cy.contains('Create Build Trigger').click();
    cy.origin(Cypress.env('REACT_QUAY_APP_API_URL'), () =>
      cy.on('uncaught:exception', (e) => false),
    );
    cy.contains('Custom Git Repository Push').click();
    cy.url().should('contain', 'repository/testorg/testrepo/trigger/');
    cy.url().should(
      'include',
      `${Cypress.env(
        'REACT_QUAY_APP_API_URL',
      )}/repository/testorg/testrepo/trigger/`,
    );
    cy.url().then((url) => {
      const redirect = url.replace(
        Cypress.env('REACT_QUAY_APP_API_URL'),
        Cypress.config().baseUrl as string,
      );
      cy.visit(redirect);
    });
    cy.contains('Setup Build Trigger:');

    // Repo URL step
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#repo-url').type('notavalidurl');
    cy.contains('Must be a valid URL');
    cy.get('#repo-url').clear();
    cy.get('#repo-url').type('https://github.com/quay/quay');
    cy.contains('Next').click();

    // Tagging Options step
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#tag-with-latest-checkbox').click();
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#tag-manifest-with-branch-or-tag-name-checkbox').click();
    cy.contains('button', 'Next').should('be.enabled');
    cy.contains('No tag templates defined.');
    cy.get('#tag-template').type('template1');
    cy.contains('Add template').click();
    cy.contains('No tag templates defined.').should('not.exist');
    cy.contains('template1');
    cy.get('#template1').within(() => cy.get('a').click());
    cy.contains('No tag templates defined.');
    cy.get('#tag-template').type('template2');
    cy.contains('Add template').click();
    cy.contains('Next').click();

    // Dockerfile path step
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#dockerfile-path').type('notavalidpath');
    cy.contains(
      'Path entered for folder containing Dockerfile is invalid: Must start with a "/".',
    );
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#dockerfile-path').clear();
    cy.get('#dockerfile-path').type('/Dockerfile/');
    cy.contains('Dockerfile path must end with a file, e.g. "Dockerfile"');
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#dockerfile-path').clear();
    cy.get('#dockerfile-path').type('/Dockerfile');
    cy.contains('Next').click();

    // Context path step
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#context-path').type('notavalidpath');
    cy.contains('Path is an invalid context.');
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#context-path').clear();
    cy.get('#context-path').type('/context');
    cy.contains('Next').click();

    // Robot account step
    cy.contains('tr', 'testorg+testrobot').within(() => {
      cy.contains('Read access will be added if selected');
      cy.get('input').click();
    });
    cy.contains('tr', 'testorg+testrobot2').within(() => {
      cy.contains('Read access will be added if selected');
    });
    cy.contains('Next').click();

    // Review and submit step
    cy.get('#repo-url').contains('https://github.com/quay/quay');
    cy.get('#tag-templates').contains('template2');
    cy.get('#tag-with-branch-or-tag').contains('enabled');
    cy.get('#tag-with-latest').contains('enabled');
    cy.get('#dockerfile-path').contains('/Dockerfile');
    cy.get('#robot-account').contains('testorg+testrobot');
    cy.get('button[type="submit"]').click();

    // Confirmation
    cy.contains('Trigger has been successfully activated');
    cy.contains(
      'Please note: If the trigger continuously fails to build, it will be automatically disabled. It can be re-enabled from the build trigger list.',
    );
    cy.contains(
      'In order to use this trigger, the following first requires action:',
    );
    cy.contains('SSH Public Key:');
    cy.contains('Webhook Endpoint URL:');
    cy.contains('Close').click();
  });

  it('displays error when analyzing trigger', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuilds');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/*/analyze',
      {
        statusCode: 500,
      },
    ).as('analyzeTrigger');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.origin(Cypress.env('REACT_QUAY_APP_API_URL'), () =>
      cy.on('uncaught:exception', (e) => false),
    );
    cy.contains('Create Build Trigger').click();
    cy.contains('Custom Git Repository Push').click();
    cy.url().should('contain', 'repository/testorg/testrepo/trigger/');
    cy.url().then((url) => {
      const redirect = url.replace(
        Cypress.env('REACT_QUAY_APP_API_URL'),
        Cypress.config().baseUrl as string,
      );
      cy.visit(redirect);
    });
    cy.contains('Setup Build Trigger:');

    cy.get('#repo-url').type('https://github.com/quay/quay');
    cy.contains('Next').click();
    cy.get('#tag-manifest-with-branch-or-tag-name-checkbox').click();
    cy.contains('Next').click();
    cy.get('#dockerfile-path').type('/Dockerfile');
    cy.contains('Next').click();
    cy.get('#context-path').type('/context');
    cy.contains('Next').click();
    cy.contains('Request failed with status code 500');
  });

  it('displays error when fetching robots', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuilds');
    cy.intercept(
      'GET',
      'api/v1/organization/testorg/robots?permissions=true&token=false',
      {
        statusCode: 500,
      },
    ).as('getRobots');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.contains('Create Build Trigger').click();
    cy.origin(Cypress.env('REACT_QUAY_APP_API_URL'), () =>
      cy.on('uncaught:exception', (e) => false),
    );
    cy.contains('Custom Git Repository Push').click();
    cy.url().should('contain', 'repository/testorg/testrepo/trigger/');
    cy.url().then((url) => {
      const redirect = url.replace(
        Cypress.env('REACT_QUAY_APP_API_URL'),
        Cypress.config().baseUrl as string,
      );
      cy.visit(redirect);
    });
    cy.contains('Setup Build Trigger:');

    cy.get('#repo-url').type('https://github.com/quay/quay');
    cy.contains('Next').click();
    cy.get('#tag-manifest-with-branch-or-tag-name-checkbox').click();
    cy.contains('Next').click();
    cy.get('#dockerfile-path').type('/Dockerfile');
    cy.contains('Next').click();
    cy.get('#context-path').type('/context');
    cy.contains('Next').click();
    cy.contains('Request failed with status code 500');
  });

  it('displays error on activation', () => {
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuilds');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/*/activate',
      {
        statusCode: 500,
      },
    ).as('activateTrigger');
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.contains('Create Build Trigger').click();
    cy.origin(Cypress.env('REACT_QUAY_APP_API_URL'), () =>
      cy.on('uncaught:exception', (e) => false),
    );
    cy.contains('Custom Git Repository Push').click();
    cy.url().should('contain', 'repository/testorg/testrepo/trigger/');
    cy.url().then((url) => {
      const redirect = url.replace(
        Cypress.env('REACT_QUAY_APP_API_URL'),
        Cypress.config().baseUrl as string,
      );
      cy.visit(redirect);
    });
    cy.contains('Setup Build Trigger:');

    cy.get('#repo-url').type('https://github.com/quay/quay');
    cy.contains('Next').click();
    cy.get('#tag-manifest-with-branch-or-tag-name-checkbox').click();
    cy.contains('Next').click();
    cy.get('#dockerfile-path').type('/Dockerfile');
    cy.contains('Next').click();
    cy.get('#context-path').type('/context');
    cy.contains('Next').click();
    cy.contains('tr', 'testorg+testrobot2').within(() => {
      cy.contains('Read access will be added if selected');
    });
    cy.contains('Next').click();
    cy.get('#repo-url').contains('https://github.com/quay/quay');
    cy.get('button[type="submit"]').click();
    cy.contains('Error activating trigger');
  });
});

describe('Repository Builds - Create GitHub Build Triggers', () => {
  beforeEach(() => {
    cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as('getUser');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
      'getCsrfToken',
    );
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo?includeStats=false&includeTags=false',
      {fixture: 'testrepo.json'},
    ).as('getRepo');
    cy.intercept('GET', '/api/v1/organization/testorg', {
      fixture: 'testorg.json',
    }).as('getOrg');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/build/?limit=10', {
      fixture: 'builds.json',
    }).as('getBuilds');
    cy.intercept('GET', '/api/v1/repository/testorg/testrepo/trigger/', {
      fixture: 'build-triggers.json',
    }).as('getBuildTriggers');
  });

  it('creates Github build trigger', () => {
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.contains('Create Build Trigger').click();
    cy.contains('GitHub Repository Push').should(
      'have.attr',
      'href',
      `https://github.com/login/oauth/authorize?client_id=testclientid&redirect_uri=${Cypress.env(
        'REACT_QUAY_APP_API_URL',
      )}/oauth2/github/callback/trigger/testorg/testrepo&scope=repo,user:email`,
    );

    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd',
      {fixture: 'initial-github-trigger.json'},
    ).as('getInitialGithubTrigger');
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd/namespaces',
      {fixture: 'github-build-trigger-namespaces.json'},
    ).as('getBuildTriggerNamespaces');
    cy.fixture('github-build-trigger-sources.json').then((fixture) => {
      for (const repo of fixture.sources) {
        repo.last_updated =
          repo.name === 'stalerepo4'
            ? 1705069849
            : Math.floor(Date.now() / 1000);
      }
      cy.intercept(
        'POST',
        '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd/sources',
        fixture,
      ).as('getBuildTriggerSources');
    });
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd/fields/refs',
      {fixture: 'build-trigger-refs.json'},
    ).as('getBuildTriggerRefs');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd/subdir',
      {fixture: 'build-trigger-subdirs.json'},
    ).as('getBuildTriggerSubDirs');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd/analyze',
      {fixture: 'build-trigger-analyze.json'},
    ).as('analyzeBuildTrigger');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd/activate',
      {fixture: 'github-build-trigger-activate.json'},
    ).as('activateTrigger');
    cy.visit(
      '/repository/testorg/testrepo/trigger/github01-0001-4c69-a5cc-ec372d0117cd',
    );

    // Select organization
    cy.contains(
      'Please select the organization under which the repository lives.',
    );
    cy.contains(
      'Mock Quay has been granted access to read and view these organizations',
    );
    cy.get('#select-organization-informational-alert').contains(
      "Don't see an expected organization here? Please visit Connections with Mock Quay and choose Grant or Request before reloading this page.",
    );

    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#gitnamespaces-search-input').type('1');
    cy.contains('Org 1');
    cy.contains('Org 2').should('not.exist');
    cy.contains('Org 3').should('not.exist');
    cy.get('#gitnamespaces-search-input').clear();

    cy.contains('tbody', 'Org 1').within(() => {
      cy.get('.strength-indicator-element').should('have.class', 'none');
    });
    cy.contains('tbody', 'Org 2').within(() => {
      cy.get('.strength-indicator-element').should('have.class', 'fair');
    });
    cy.contains('tbody', 'Org 3').within(() => {
      cy.get('.strength-indicator-element').should('have.class', 'good');
    });

    cy.get('#githuborg1-checkbox').click();
    cy.contains('button', 'Next').should('be.enabled');
    cy.contains('button', 'Clear').click();
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#githuborg1-checkbox').click();

    cy.contains('a', 'Connections with Mock Quay').should(
      'have.attr',
      'href',
      'https://github.com/settings/connections/applications/testclientid',
    );
    cy.contains('a', 'Org 1').should(
      'have.attr',
      'href',
      'https://github.com/githuborg1',
    );

    cy.contains('Next').click();

    // Select hosted repository
    cy.get('#hosted-repository-header-description').within(() => {
      cy.contains('Select a repository in ');
      cy.contains('Org 1');
      cy.get('img').should(
        'have.attr',
        'src',
        'https://avatars.githubusercontent.com/u/1234567?v=3',
      );
    });

    cy.contains('tr', 'repo1').within(() => {
      cy.contains('repo1 description');
    });
    cy.contains('tr', 'repo2').within(() => {
      cy.contains('repo2 description');
    });
    cy.contains('tr', 'noadminpermissionsrepo3').within(() => {
      cy.get('#noadminpermissionsrepo3-admin-access-required-tooltip').should(
        'exist',
      );
      cy.contains('noadminpermissionsrepo3 description');
    });
    cy.contains('tr', 'privaterepo5').within(() => {
      cy.contains('None');
    });

    cy.contains('stalerepo4').should('not.exist');
    cy.get('#hide-stale-checkbox').click();
    cy.contains('stalerepo4');

    cy.get('#repo1-checkbox').click();
    cy.contains('button', 'Next').should('be.enabled');
    cy.contains('button', 'Clear').click();
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#repo1-checkbox').click();

    cy.get('#hostedrepositories-search-input').type('repo1');
    cy.contains('repo1');
    cy.contains('repo2').should('not.exist');
    cy.contains('noadminpermissionsrepo3').should('not.exist');
    cy.contains('privaterepo5').should('not.exist');
    cy.get('#hostedrepositories-search-input').clear();

    cy.contains('Next').click();

    // Trigger options
    cy.get('#branch-tag-filter').should('not.exist');
    cy.get('#branch-tag-filter-checkbox').click();
    cy.get('#branch-tag-filter').should('be.visible');
    cy.get('#branch-tag-filter').type('nomatch');
    cy.get('.match-list.matching').contains('nomatch').should('not.exist');
    cy.get('.match-list.not-matching').contains('master');
    cy.get('.match-list.not-matching').contains('development');
    cy.get('.match-list.not-matching').contains('1.0.0');
    cy.get('.match-list.not-matching').contains('1.0.1');
    cy.get('#branch-tag-filter').clear();
    cy.get('#branch-tag-filter').type('heads/master');
    cy.get('.match-list.matching').contains('master');
    cy.contains('Next').click();

    // Tagging options (Tested in previous tests, skipping)
    cy.get('#tag-manifest-with-branch-or-tag-name-checkbox').click();
    cy.contains('Next').click();

    // Dockerfile path
    cy.get('input[aria-label="Type to filter"]').type('nesteddir1');
    cy.contains('/dir2/subdir2/nesteddir1/Dockerfile');
    cy.contains('/dir2/subrdir1/Dockerfile').should('not.exist');
    cy.contains('/dir1/Dockerfile').should('not.exist');
    cy.get('button[aria-label="Clear input value"]').click();
    cy.get('button[aria-label="Menu toggle"]').click();
    cy.contains('/Dockerfile');
    cy.contains('/dir1/Dockerfile');
    cy.contains('/dir2/subrdir1/Dockerfile');
    cy.contains('/dir2/subdir2/nesteddir1/Dockerfile').click();
    cy.get('input[aria-label="Type to filter"]').should(
      'have.value',
      '/dir2/subdir2/nesteddir1/Dockerfile',
    );
    cy.contains('Next').click();

    // Context path
    cy.get('input[aria-label="Type to filter"]').type('nesteddir1');
    cy.get('#select-typeahead-listbox').each((el) => {
      cy.wrap(el).contains('/dir2/subdir2/nesteddir1');
    });
    cy.get('button[aria-label="Clear input value"]').click();
    cy.get('button[aria-label="Menu toggle"]').click();
    cy.get('#select-typeahead-listbox > li').each((el) => {
      const expected = [
        '/',
        '/dir2',
        '/dir2/subdir2',
        '/dir2/subdir2/nesteddir1',
      ];
      expect(expected).to.include(el.text());
    });
    cy.contains('/dir2/subdir2/nesteddir1').click();
    cy.get('input[aria-label="Type to filter"]').should(
      'have.value',
      '/dir2/subdir2/nesteddir1',
    );
    cy.contains('Next').click();

    // Select robot (Tested in previous tests, skipping)
    cy.contains('Next').click();

    // Review and submit step
    cy.get('#repo-url').contains('githuborg1/repo1');
    cy.get('#tag-with-branch-or-tag').contains('enabled');
    cy.get('#tag-with-latest').contains('disabled');
    cy.get('#dockerfile-path').contains('/dir2/subdir2/nesteddir1/Dockerfile');
    cy.get('#context-path').contains('/dir2/subdir2/nesteddir1');
    cy.get('button[type="submit"]').click();

    // Confirmation
    cy.contains('Trigger has been successfully activated');
    cy.contains(
      'Please note: If the trigger continuously fails to build, it will be automatically disabled. It can be re-enabled from the build trigger list.',
    );
    cy.contains('SSH Public Key:');
    cy.contains('Close').click();
  });

  it('creates GitLab build trigger', () => {
    cy.visit('/repository/testorg/testrepo?tab=builds');

    cy.contains('Create Build Trigger').click();
    cy.contains('GitLab Repository Push').should(
      'have.attr',
      'href',
      `https://gitlab.com/oauth/authorize?client_id=testclientid&redirect_uri=${Cypress.env(
        'REACT_QUAY_APP_API_URL',
      )}/oauth2/gitlab/callback/trigger&scope=api%20write_repository%20openid&response_type=code&state=repo:testorg/testrepo`,
    );

    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd',
      {fixture: 'initial-gitlab-trigger.json'},
    ).as('getInitialGitlabTrigger');
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd/namespaces',
      {fixture: 'gitlab-build-trigger-namespaces.json'},
    ).as('getBuildTriggerNamespaces');
    cy.fixture('gitlab-build-trigger-sources.json').then((fixture) => {
      for (const repo of fixture.sources) {
        repo.last_updated =
          repo.name === 'stalerepo4'
            ? 1705069849
            : Math.floor(Date.now() / 1000);
      }
      cy.intercept(
        'POST',
        '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd/sources',
        fixture,
      ).as('getBuildTriggerSources');
    });
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd/fields/refs',
      {fixture: 'build-trigger-refs.json'},
    ).as('getBuildTriggerRefs');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd/subdir',
      {fixture: 'build-trigger-subdirs.json'},
    ).as('getBuildTriggerSubDirs');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd/analyze',
      {fixture: 'build-trigger-analyze.json'},
    ).as('analyzeBuildTrigger');
    cy.intercept(
      'POST',
      '/api/v1/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd/activate',
      {fixture: 'gitlab-build-trigger-activate.json'},
    ).as('activateTrigger');
    cy.visit(
      '/repository/testorg/testrepo/trigger/gitlab01-0001-4c69-a5cc-ec372d0117cd',
    );

    // Select organization
    cy.contains(
      'Please select the organization under which the repository lives.',
    );
    cy.contains(
      'Mock Quay has been granted access to read and view these organizations',
    );

    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#gitnamespaces-search-input').type('User');
    cy.contains('User 1');
    cy.contains('Group 2').should('not.exist');
    cy.contains('Group 3').should('not.exist');
    cy.get('#gitnamespaces-search-input').clear();

    cy.contains('tbody', 'User 1').within(() => {
      cy.get('.strength-indicator-element').should('have.class', 'none');
    });
    cy.contains('tbody', 'Group 2').within(() => {
      cy.get('.strength-indicator-element').should('have.class', 'fair');
    });
    cy.contains('tbody', 'Group 3').within(() => {
      cy.get('.strength-indicator-element').should('have.class', 'good');
    });

    cy.get('#gitlabgroup2-checkbox').click();
    cy.contains('button', 'Next').should('be.enabled');
    cy.contains('button', 'Clear').click();
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#gitlabgroup2-checkbox').click();

    cy.contains('a', 'Group 2').should(
      'have.attr',
      'href',
      'https://gitlab.com/groups/gitlabgroup2',
    );

    cy.contains('Next').click();

    // Select hosted repository
    cy.get('#hosted-repository-header-description').within(() => {
      cy.contains('Select a repository in ');
      cy.contains('Group 2');
    });

    cy.contains('tr', 'repo1').within(() => {
      cy.contains('repo1 description');
    });
    cy.contains('tr', 'repo2').within(() => {
      cy.contains('repo2 description');
    });
    cy.contains('tr', 'noadminpermissionsrepo3').within(() => {
      cy.get('#noadminpermissionsrepo3-admin-access-required-tooltip').should(
        'exist',
      );
      cy.contains('noadminpermissionsrepo3 description');
    });
    cy.contains('tr', 'privaterepo5').within(() => {
      cy.contains('None');
    });

    cy.contains('stalerepo4').should('not.exist');
    cy.get('#hide-stale-checkbox').click();
    cy.contains('stalerepo4');

    cy.get('#repo1-checkbox').click();
    cy.contains('button', 'Next').should('be.enabled');
    cy.contains('button', 'Clear').click();
    cy.contains('button', 'Next').should('be.disabled');
    cy.get('#repo1-checkbox').click();

    cy.get('#hostedrepositories-search-input').type('repo1');
    cy.contains('repo1');
    cy.contains('repo2').should('not.exist');
    cy.contains('noadminpermissionsrepo3').should('not.exist');
    cy.contains('privaterepo5').should('not.exist');
    cy.get('#hostedrepositories-search-input').clear();

    cy.contains('Next').click();

    // Trigger options
    cy.get('#branch-tag-filter').should('not.exist');
    cy.get('#branch-tag-filter-checkbox').click();
    cy.get('#branch-tag-filter').should('be.visible');
    cy.get('#branch-tag-filter').type('nomatch');
    cy.get('.match-list.matching').contains('nomatch').should('not.exist');
    cy.get('.match-list.not-matching').contains('master');
    cy.get('.match-list.not-matching').contains('development');
    cy.get('.match-list.not-matching').contains('1.0.0');
    cy.get('.match-list.not-matching').contains('1.0.1');
    cy.get('#branch-tag-filter').clear();
    cy.get('#branch-tag-filter').type('heads/master');
    cy.get('.match-list.matching').contains('master');
    cy.contains('Next').click();

    // Tagging options (Tested in previous tests, skipping)
    cy.get('#tag-manifest-with-branch-or-tag-name-checkbox').click();
    cy.contains('Next').click();

    // Dockerfile path
    cy.get('input[aria-label="Type to filter"]').type('nesteddir1');
    cy.contains('/dir2/subdir2/nesteddir1/Dockerfile');
    cy.contains('/dir2/subrdir1/Dockerfile').should('not.exist');
    cy.contains('/dir1/Dockerfile').should('not.exist');
    cy.get('button[aria-label="Clear input value"]').click();
    cy.get('button[aria-label="Menu toggle"]').click();
    cy.contains('/Dockerfile');
    cy.contains('/dir1/Dockerfile');
    cy.contains('/dir2/subrdir1/Dockerfile');
    cy.contains('/dir2/subdir2/nesteddir1/Dockerfile').click();
    cy.get('input[aria-label="Type to filter"]').should(
      'have.value',
      '/dir2/subdir2/nesteddir1/Dockerfile',
    );
    cy.contains('Next').click();

    // Context path
    cy.get('input[aria-label="Type to filter"]').type('nesteddir1');
    cy.get('#select-typeahead-listbox').each((el) => {
      cy.wrap(el).contains('/dir2/subdir2/nesteddir1');
    });
    cy.get('button[aria-label="Clear input value"]').click();
    cy.get('button[aria-label="Menu toggle"]').click();
    cy.get('#select-typeahead-listbox > li').each((el) => {
      const expected = [
        '/',
        '/dir2',
        '/dir2/subdir2',
        '/dir2/subdir2/nesteddir1',
      ];
      expect(expected).to.include(el.text());
    });
    cy.contains('/dir2/subdir2/nesteddir1').click();
    cy.get('input[aria-label="Type to filter"]').should(
      'have.value',
      '/dir2/subdir2/nesteddir1',
    );
    cy.contains('Next').click();

    // Select robot (Tested in previous tests, skipping)
    cy.contains('Next').click();

    // Review and submit step
    cy.get('#repo-url').contains('gitlabgroup2/repo1');
    cy.get('#tag-with-branch-or-tag').contains('enabled');
    cy.get('#tag-with-latest').contains('disabled');
    cy.get('#dockerfile-path').contains('/dir2/subdir2/nesteddir1/Dockerfile');
    cy.get('#context-path').contains('/dir2/subdir2/nesteddir1');
    cy.get('button[type="submit"]').click();

    // Confirmation
    cy.contains('Trigger has been successfully activated');
    cy.contains(
      'Please note: If the trigger continuously fails to build, it will be automatically disabled. It can be re-enabled from the build trigger list.',
    );
    cy.contains('SSH Public Key:');
    cy.contains('Close').click();
  });
});

describe('Repository Builds - View build logs', () => {
  beforeEach(() => {
    cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as('getUser');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
      'getCsrfToken',
    );
    cy.fixture('testrepo.json').then((fixture) => {
      fixture.can_write = true;
      cy.intercept(
        'GET',
        '/api/v1/repository/testorg/testrepo?includeStats=false&includeTags=false',
        fixture,
      ).as('getrepo');
    });
  });

  it('View Build Info', () => {
    cy.fixture('builds.json').then((fixture) => {
      for (const [index, build] of fixture.builds.entries()) {
        const expectedData = buildData[index];
        cy.intercept(
          'GET',
          `/api/v1/repository/testorg/testrepo/build/${build.id}`,
          build,
        ).as(`getBuild${build.id}`);
        cy.intercept(
          'GET',
          `/api/v1/repository/testorg/testrepo/build/${build.id}/logs?start=*`,
          {fixture: 'build-logs.json'},
        ).as('getBuildLogs');
        cy.visit(`/repository/testorg/testrepo/build/${build.id}`);
        cy.get('#build-id').contains(build.id);
        cy.get('#started').contains(formatDate(build.started));
        cy.get('#status').contains(getBuildMessage(build.phase));
        cy.get('#triggered-by').within(() => {
          const messageElement = cy.contains(expectedData.trigger.message);
          if (expectedData.trigger.messageLink) {
            messageElement.should(
              'have.attr',
              'href',
              expectedData.trigger.messageLink,
            );
          }
          if (expectedData.trigger.authoredDate) {
            // Time difference between now and author date in seconds
            const authorDate =
              (new Date().getTime() -
                new Date(expectedData.trigger.authoredDate).getTime()) /
              1000;
            cy.contains(humanizeTimeForExpiry(authorDate));
          }
          if (expectedData.trigger.author) {
            cy.contains(expectedData.trigger.author);
          }
          if (expectedData.trigger.commit) {
            const commitElement = cy.contains(expectedData.trigger.commit);
            if (expectedData.trigger.commitLink) {
              commitElement.should(
                'have.attr',
                'href',
                expectedData.trigger.commitLink,
              );
            }
          }
          if (expectedData.trigger.ref) {
            const refElement = cy.contains(expectedData.trigger.ref);
            if (expectedData.trigger.refLink) {
              refElement.should(
                'have.attr',
                'href',
                expectedData.trigger.refLink,
              );
            }
          }
        });
        if (getCompletedBuildPhases().includes(build.phase)) {
          cy.contains('Cancel build').should('not.exist');
        } else {
          cy.contains('Cancel build');
        }
      }
    });
  });

  it('View build logs', () => {
    cy.fixture('builds.json').then((fixture) => {
      const build = fixture.builds[0];
      cy.intercept(
        'GET',
        `/api/v1/repository/testorg/testrepo/build/${build.id}`,
        build,
      ).as(`getBuild${build.id}`);
      cy.intercept(
        'GET',
        `/api/v1/repository/testorg/testrepo/build/${build.id}/logs?start=*`,
        {fixture: 'build-logs.json'},
      ).as('getBuildLogs');
      cy.visit(`/repository/testorg/testrepo/build/${build.id}`);

      // Default content
      cy.contains('build-scheduled');
      cy.contains('unpacking');
      cy.contains('pulling');
      cy.contains('building');
      cy.contains('FROM');
      cy.contains('registry.access.redhat.com/ubi8/ubi:8.0');
      cy.contains('RUN');
      cy.contains('curl -v https://www.google.com');
      cy.contains('pushing');
      cy.contains('complete');

      // Expanded content
      cy.contains(
        'Status: Downloaded newer image for quay.io/testorg/testrepo:latest',
      ).should('not.exist');
      cy.contains('---> 11f9dba4d1bc').should('not.exist');
      cy.contains(
        'Successfully tagged 648b039e-8922-4167-4031-955a1ba7f701:latest',
      ).should('not.exist');
      cy.contains(
        'master: digest: sha256:d85a25b170694321983c23c1377289a18fca89950e4dc59b4bf138d428ca4659 size: 737',
      ).should('not.exist');
      cy.contains('pulling').click();
      cy.contains('FROM').click();
      cy.contains('RUN').click();
      cy.contains('pushing').click();
      cy.contains(
        'Status: Downloaded newer image for quay.io/testorg/testrepo:latest',
      );
      cy.contains('---> 11f9dba4d1bc');
      cy.contains(
        'Successfully tagged 648b039e-8922-4167-4031-955a1ba7f701:latest',
      );
      cy.contains(
        'master: digest: sha256:d85a25b170694321983c23c1377289a18fca89950e4dc59b4bf138d428ca4659 size: 737',
      );

      // Timestamps
      cy.get('.build-log-timestamp').should('not.exist');
      cy.contains('Show timestamps').click();
      cy.get('.build-log-timestamp').should('exist');
      cy.contains('Hide timestamps').click();
      cy.get('.build-log-timestamp').should('not.exist');

      // Copy
      cy.get('button:contains("Copy")')
        .focus()
        .dblclick()
        .then(() => {
          cy.window().then((win) => {
            win.navigator.clipboard.readText().then((text) => {
              text.includes('build-scheduled');
              text.includes('unpacking');
              text.includes('curl -v https://www.google.com');
              text.includes(
                'Status: Downloaded newer image for quay.io/testorg/testrepo:latest',
              );
              text.includes('---> 11f9dba4d1bc');
              text.includes(
                'Successfully tagged 648b039e-8922-4167-4031-955a1ba7f701:latest',
              );
              text.includes(
                'master: digest: sha256:d85a25b170694321983c23c1377289a18fca89950e4dc59b4bf138d428ca4659 size: 737',
              );
            });
          });
        });

      // Download
      cy.contains('a', 'Download').should(
        'have.attr',
        'href',
        `/buildlogs/${build.id}`,
      );
      cy.contains('a', 'Download').should('have.attr', 'target', `_blank`);
    });
  });

  it('View archived build logs', () => {
    cy.fixture('builds.json').then((fixture) => {
      const build = fixture.builds[0];
      cy.intercept(
        'GET',
        `/api/v1/repository/testorg/testrepo/build/${build.id}`,
        build,
      ).as(`getBuild${build.id}`);
      cy.intercept(
        'GET',
        `/api/v1/repository/testorg/testrepo/build/${build.id}/logs?start=*`,
        {logs_url: '/redirected/logs'},
      ).as('getBuildLogs');
      cy.intercept('GET', `/redirected/logs`, {fixture: 'build-logs.json'}).as(
        'getArchivedLogs',
      );
      cy.visit(`/repository/testorg/testrepo/build/${build.id}`);

      cy.contains('build-scheduled');
      cy.contains('unpacking');
      cy.contains('pulling');
      cy.contains('building');
      cy.contains('FROM');
      cy.contains('registry.access.redhat.com/ubi8/ubi:8.0');
      cy.contains('RUN');
      cy.contains('curl -v https://www.google.com');
      cy.contains('pushing');
      cy.contains('complete');
    });
  });
});
