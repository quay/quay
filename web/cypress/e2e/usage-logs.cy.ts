describe('Usage Logs', () => {
  const aggregateLogsResp = {
    aggregated: [
      {
        kind: 'create_application',
        count: 1,
        datetime: new Date(),
      },
      {
        kind: 'org_create',
        count: 1,
        datetime: new Date(),
      },
    ],
  };

  const logsResp = {
    start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
    end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
    logs: [
      {
        kind: 'change_repo_visibility',
        metadata: {
          repo: 'testrepo',
          namespace: 'projectquay',
          visibility: 'public',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:33:07 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'change_repo_visibility',
        metadata: {
          repo: 'testrepo',
          namespace: 'projectquay',
          visibility: 'private',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:33:04 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'create_repo',
        metadata: {
          repo: 'testrepo',
          namespace: 'projectquay',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:57 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'org_create',
        metadata: {
          email: null,
          namespace: 'projectquay',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:46 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'create_namespace_autoprune_policy',
        metadata: {
          method: 'number_of_tags',
          value: 20,
          tag_pattern: 'v1.*',
          tag_pattern_matches: true,
          namespace: 'org1',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:46 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'create_repository_autoprune_policy',
        metadata: {
          method: 'number_of_tags',
          value: 20,
          tag_pattern: 'v1.*',
          tag_pattern_matches: true,
          namespace: 'org1',
          repo: 'test',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:46 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
    ],
    next_page:
      'gAAAAABl1jP3IfVFJNPZRJSB9YWXx0D8QXLXYmf8-0zZeqwV2dIM5gAsxdfaxGHUdS5FUsrm_8N1RIqm71EoagF1D9uwXh2agg==',
  };

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('exports repository logs', () => {
    cy.intercept(
      'POST',
      'api/v1/repository/user1/hello-world/exportlogs?starttime=$endtime=',
    ).as('exportRepositoryLogs');
    cy.visit('/repository/user1/hello-world?tab=logs'); // lowercase l for repository
    cy.contains('Export').click();
    cy.get('[id="export-logs-callback"]').type('example@example.com');
    cy.contains('Confirm').click();
    cy.contains('Logs exported with id').should('be.visible');
  });
  it('exports repository logs failure', () => {
    cy.intercept(
      'POST',
      'api/v1/repository/user1/hello-world/exportlogs?starttime=$endtime=',
    ).as('exportRepositoryLogs');
    cy.visit('/repository/user1/hello-world?tab=logs'); // lowercase l for repository
    cy.contains('Export').click();
    cy.get('[id="export-logs-callback"]').type('blahblah');
    cy.contains('Confirm').should('be.disabled');
  });

  it('shows usage logs graph', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/aggregatelogs?*',
      aggregateLogsResp,
    );
    cy.visit('/organization/projectquay?tab=Logs'); // Capital L for organization
    cy.get('[class=pf-v5-c-chart]')
      .should('be.visible')
      .and((chart) => {
        expect(chart.height()).to.be.greaterThan(1);
      });
    cy.contains('Create Application').should('be.visible');
    cy.contains('Create organization').should('be.visible');
  });

  it('shows usage logs  table', () => {
    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', logsResp);
    cy.visit('/organization/projectquay?tab=Logs');
    cy.get('table')
      .contains(
        'td',
        'Change visibility for repository projectquay/testrepo to public',
      )
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Change visibility for repository projectquay/testrepo to private',
      )
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains('td', 'Create Repository projectquay/testrepo')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains('td', 'Organization projectquay created')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Created namespace autoprune policy: "number_of_tags:20, tagPattern:v1.*, tagPatternMatches:true" for namespace: org1',
      )
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Created repository autoprune policy: "number_of_tags:20, tagPattern:v1.*, tagPatternMatches:true" for repository: org1/test',
      )
      .scrollIntoView()
      .should('be.visible');
  });

  it('toggle chart', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/aggregatelogs?*',
      aggregateLogsResp,
    );
    cy.visit('/organization/projectquay?tab=Logs');

    cy.contains('Hide Chart').click();
    cy.get('[class=pf-v5-c-chart]').should('not.exist');

    cy.contains('Show Chart').click();
    cy.get('[class=pf-v5-c-chart]').should('be.visible');
  });

  it('empty chart', () => {
    cy.visit('/organization/projectquay?tab=Logs');
    cy.contains('No data to display.').should('be.visible');
  });

  it('shows Splunk error message when logs are not implemented', () => {
    // Mock 501 NOT IMPLEMENTED error from Splunk
    cy.intercept('GET', '/api/v1/organization/projectquay/aggregatelogs?*', {
      statusCode: 501,
      body: {
        message: 'Method not implemented, Splunk does not support log lookups',
      },
    }).as('aggregateLogsError');

    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', {
      statusCode: 501,
      body: {
        message: 'Method not implemented, Splunk does not support log lookups',
      },
    }).as('logsError');

    cy.visit('/organization/projectquay?tab=Logs');

    // Verify the specific Splunk error message is displayed (not generic error)
    cy.contains(
      'Method not implemented, Splunk does not support log lookups',
    ).should('be.visible');

    // Verify generic error is NOT displayed
    cy.contains('Unable to complete request').should('not.exist');
  });

  it('displays quota audit log descriptions', () => {
    const quotaLogsResp = {
      start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
      end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
      logs: [
        {
          kind: 'org_create_quota',
          metadata: {
            namespace: 'projectquay',
            limit_bytes: 1073741824,
            limit: '1.0 GiB',
          },
          ip: '192.168.228.1',
          datetime: 'Wed, 21 Feb 2024 17:33:07 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
        },
        {
          kind: 'org_change_quota',
          metadata: {
            namespace: 'projectquay',
            limit_bytes: 5368709120,
            limit: '5.0 GiB',
            previous_limit_bytes: 1073741824,
            previous_limit: '1.0 GiB',
          },
          ip: '192.168.228.1',
          datetime: 'Wed, 21 Feb 2024 17:34:07 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
        },
        {
          kind: 'org_delete_quota',
          metadata: {
            namespace: 'projectquay',
            quota_id: 1,
            limit_bytes: 5368709120,
            limit: '5.0 GiB',
          },
          ip: '192.168.228.1',
          datetime: 'Wed, 21 Feb 2024 17:35:07 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
        },
        {
          kind: 'org_create_quota_limit',
          metadata: {
            namespace: 'projectquay',
            type: 'Warning',
            threshold_percent: 80,
          },
          ip: '192.168.228.1',
          datetime: 'Wed, 21 Feb 2024 17:36:07 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
        },
        {
          kind: 'org_change_quota_limit',
          metadata: {
            namespace: 'projectquay',
            type: 'Warning',
            threshold_percent: 90,
            previous_type: 'Warning',
            previous_threshold_percent: 80,
          },
          ip: '192.168.228.1',
          datetime: 'Wed, 21 Feb 2024 17:37:07 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
        },
        {
          kind: 'org_delete_quota_limit',
          metadata: {
            namespace: 'projectquay',
            limit_id: 1,
            type: 'Reject',
            threshold_percent: 100,
          },
          ip: '192.168.228.1',
          datetime: 'Wed, 21 Feb 2024 17:38:07 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
        },
      ],
    };

    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/logs?*',
      quotaLogsResp,
    );
    cy.visit('/organization/projectquay?tab=Logs');

    // Verify quota audit log descriptions are displayed correctly
    cy.get('table')
      .contains('td', 'Created storage quota of')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table').contains('td', '1.0 GiB').should('be.visible');

    cy.get('table')
      .contains('td', 'Changed storage quota for organization')
      .scrollIntoView()
      .should('be.visible');

    cy.get('table')
      .contains('td', 'Deleted storage quota of')
      .scrollIntoView()
      .should('be.visible');

    cy.get('table')
      .contains('td', 'Created Warning quota limit at')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table').contains('td', '80%').should('be.visible');

    cy.get('table')
      .contains('td', 'Changed quota limit for organization')
      .scrollIntoView()
      .should('be.visible');

    cy.get('table')
      .contains('td', 'Deleted Reject quota limit at')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table').contains('td', '100%').should('be.visible');
  });

  it('filter logs', () => {
    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', logsResp);

    cy.visit('/organization/projectquay?tab=Logs');

    cy.get('[id="log-filter-input"]').type('create');

    cy.get('table')
      .contains('td', 'Create Repository projectquay/testrepo')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains('td', 'Organization projectquay created')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Change visibility for repository projectquay/testrepo to private',
      )
      .should('not.exist');
  });

  // Test for verifying all logs can be loaded across multiple pages
  it('loads all logs across multiple pages', () => {
    const firstPageLogs = {
      start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
      end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
      logs: Array.from({length: 20}, (_, i) => ({
        kind: 'push_repo',
        metadata: {
          repo: `repo${i}`,
          namespace: 'projectquay',
        },
        ip: '192.168.1.1',
        datetime: `Wed, 21 Feb 2024 17:${59 - i}:00 -0000`,
        performer: {
          kind: 'user',
          name: 'user1',
          is_robot: false,
        },
      })),
      next_page: 'page2_token',
    };

    const secondPageLogs = {
      start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
      end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
      logs: Array.from({length: 6}, (_, i) => ({
        kind: 'pull_repo',
        metadata: {
          repo: `repo${i + 20}`,
          namespace: 'projectquay',
        },
        ip: '192.168.1.1',
        datetime: `Wed, 21 Feb 2024 16:${59 - i}:00 -0000`,
        performer: {
          kind: 'user',
          name: 'user2',
          is_robot: false,
        },
      })),
      next_page: undefined, // No more pages
    };

    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/aggregatelogs?*',
      aggregateLogsResp,
    ).as('getAggregateLogs');

    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', (req) => {
      // Check if next_page parameter has a value (not just empty)
      const url = new URL(req.url);
      const nextPage = url.searchParams.get('next_page');

      if (nextPage && nextPage.length > 0) {
        // Second page request (has next_page token)
        req.reply(secondPageLogs);
      } else {
        // First page request (no next_page or empty next_page)
        req.reply(firstPageLogs);
      }
    }).as('getLogs');

    cy.visit('/organization/projectquay?tab=Logs');
    cy.wait('@getAggregateLogs');
    cy.wait('@getLogs');

    // Scroll to pagination section to ensure logs are visible
    cy.contains(/of\s+20/)
      .scrollIntoView()
      .should('be.visible');

    // Click Load More to fetch second page
    cy.contains('button', 'Load More Logs').click();
    cy.wait('@getLogs');

    // Verify pagination now shows all 26 logs (20 + 6)
    cy.contains(/of\s+26/).should('be.visible');

    // Verify Load More button is hidden (no more pages)
    cy.contains('button', 'Load More Logs').should('not.exist');

    // Verify we can access logs from second page through table pagination
    cy.get('button[aria-label="Go to next page"]:visible').first().click();

    // Should now show second page of client-side pagination
    cy.contains(/of\s+26/).should('be.visible');
  });
});

describe('Usage Logs - Superuser', () => {
  const superuserLogsResp = {
    start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
    end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
    logs: [
      {
        kind: 'account_change_plan',
        metadata: {
          namespace: 'user1',
        },
        ip: '172.31.0.1',
        datetime: 'Wed, 29 Oct 2025 14:01:14 -0000',
        performer: {
          kind: 'user',
          name: 'user1',
          is_robot: false,
          avatar: {
            name: 'user1',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'account_change_plan',
        metadata: {
          namespace: 'user1',
        },
        ip: '172.31.0.1',
        datetime: 'Wed, 29 Oct 2025 13:55:45 -0000',
        performer: {
          kind: 'user',
          name: 'user1',
          is_robot: false,
          avatar: {
            name: 'user1',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
    ],
  };

  const superuserAggregateLogsResp = {
    aggregated: [
      {
        kind: 'account_change_plan',
        count: 4,
        datetime: new Date(),
      },
      {
        kind: 'account_change_plan',
        count: 1,
        datetime: new Date(),
      },
    ],
  };

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('displays superuser usage logs page', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Verify page title
    cy.contains('h1', 'Usage Logs').should('be.visible');

    // Verify chart controls exist
    cy.contains('button', 'Hide Chart').should('be.visible');

    // Verify table exists
    cy.get('[role="grid"]').should('be.visible');

    // Verify namespace column exists (superuser only)
    cy.contains('th', 'Namespace').should('be.visible');
  });

  it('toggles chart visibility on superuser page', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Verify chart is visible initially - use class selector to avoid matching header logo
    cy.get('[class=pf-v5-c-chart]').should('exist');

    // Hide chart
    cy.contains('button', 'Hide Chart').click();

    // Verify chart is hidden (not in DOM)
    cy.get('[class=pf-v5-c-chart]').should('not.exist');

    // Verify button text changed
    cy.contains('button', 'Show Chart').should('be.visible');

    // Show chart again
    cy.contains('button', 'Show Chart').click();

    // Verify chart is visible
    cy.get('[class=pf-v5-c-chart]').should('exist');
    cy.contains('button', 'Hide Chart').should('be.visible');
  });

  it('filters superuser logs', () => {
    const multipleLogsResp = {
      start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
      end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
      logs: [
        {
          kind: 'user_create',
          metadata: {
            username: 'testuser',
            namespace: 'testuser',
          },
          ip: '172.18.0.1',
          datetime: 'Wed, 29 Oct 2025 14:01:14 -0000',
          performer: {
            kind: 'user',
            name: 'admin',
            is_robot: false,
          },
          namespace: {
            name: 'testuser',
          },
        },
        {
          kind: 'org_create',
          metadata: {
            namespace: 'projectquay',
          },
          ip: '192.168.1.1',
          datetime: 'Wed, 29 Oct 2025 13:55:45 -0000',
          performer: {
            kind: 'user',
            name: 'user1',
            is_robot: false,
          },
          namespace: {
            name: 'projectquay',
          },
        },
        {
          kind: 'account_change_plan',
          metadata: {
            namespace: 'user1',
          },
          ip: '172.31.0.1',
          datetime: 'Wed, 29 Oct 2025 13:50:00 -0000',
          performer: {
            kind: 'user',
            name: 'user1',
            is_robot: false,
          },
          namespace: {
            name: 'user1',
          },
        },
      ],
    };

    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', multipleLogsResp);

    cy.visit('/usage-logs');

    // Wait for the table to be visible first
    cy.get('[aria-label="Usage logs table"]').should('be.visible');

    // Wait for logs to load - use scrollIntoView to ensure visibility
    cy.contains('td', 'User testuser created')
      .scrollIntoView()
      .should('be.visible');
    cy.contains('td', 'Organization projectquay created')
      .scrollIntoView()
      .should('be.visible');
    cy.contains('td', 'Change plan').scrollIntoView().should('be.visible');

    // Filter by namespace
    cy.get('[placeholder="Filter logs"]').type('projectquay');
    cy.contains('td', 'Organization projectquay created').should('be.visible');
    cy.contains('td', 'User testuser created').should('not.exist');
    cy.contains('td', 'Change plan').should('not.exist');

    // Clear and filter by performer
    cy.get('[placeholder="Filter logs"]').clear();
    cy.get('[placeholder="Filter logs"]').type('admin');
    cy.contains('td', 'User testuser created').should('be.visible');
    cy.contains('td', 'Organization projectquay created').should('not.exist');
    cy.contains('td', 'Change plan').should('not.exist');

    // Clear and filter by IP address
    cy.get('[placeholder="Filter logs"]').clear();
    cy.get('[placeholder="Filter logs"]').type('192.168');
    cy.contains('td', 'Organization projectquay created').should('be.visible');
    cy.contains('td', 'User testuser created').should('not.exist');
    cy.contains('td', 'Change plan').should('not.exist');

    // Clear and filter by description
    cy.get('[placeholder="Filter logs"]').clear();
    cy.get('[placeholder="Filter logs"]').type('created');
    cy.contains('td', 'User testuser created').should('be.visible');
    cy.contains('td', 'Organization projectquay created').should('be.visible');
    cy.contains('td', 'Change plan').should('not.exist');

    // Clear filter
    cy.get('[placeholder="Filter logs"]').clear();
    cy.contains('td', 'User testuser created').should('be.visible');
    cy.contains('td', 'Organization projectquay created').should('be.visible');
    cy.contains('td', 'Change plan').should('be.visible');
  });

  it('displays table columns for superuser', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Verify all expected column headers exist
    cy.contains('th', 'Date & Time').should('be.visible');
    cy.contains('th', 'Description').should('be.visible');
    cy.contains('th', 'Namespace').should('be.visible');
    cy.contains('th', 'Repository').should('be.visible');
    cy.contains('th', 'Performed by').should('be.visible');
    cy.contains('th', 'IP Address').should('be.visible');
  });

  it('shows Splunk error message on superuser page when logs are not implemented', () => {
    // Mock 501 NOT IMPLEMENTED error from Splunk
    cy.intercept('GET', '/api/v1/superuser/aggregatelogs?*', {
      statusCode: 501,
      body: {
        message: 'Method not implemented, Splunk does not support log lookups',
      },
    }).as('aggregateLogsError');

    cy.intercept('GET', '/api/v1/superuser/logs?*', {
      statusCode: 501,
      body: {
        message: 'Method not implemented, Splunk does not support log lookups',
      },
    }).as('logsError');

    cy.visit('/usage-logs');

    // Verify the specific Splunk error message is displayed (not generic error)
    cy.contains(
      'Method not implemented, Splunk does not support log lookups',
    ).should('be.visible');

    // Verify generic error is NOT displayed
    cy.contains('Unable to complete request').should('not.exist');
  });
});
