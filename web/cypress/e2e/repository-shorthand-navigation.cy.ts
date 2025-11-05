/// <reference types="cypress" />

/**
 * Factory function to create repository mock data
 * @param org - Organization/namespace name
 * @param name - Repository name
 * @param overrides - Optional overrides for default values
 * @returns Repository mock object
 */
function mockRepository(
  org: string,
  name: string,
  overrides: Partial<{
    description: string;
    is_public: boolean;
    kind: string;
    state: string;
    can_write: boolean;
    can_admin: boolean;
  }> = {},
) {
  return {
    namespace: org,
    name: name,
    description: 'Test repository',
    is_public: true,
    kind: 'image',
    state: 'NORMAL',
    can_write: true,
    can_admin: true,
    ...overrides,
  };
}

describe('Repository Shorthand URL Navigation', () => {
  beforeEach(() => {
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('redirects shorthand URL /:org/:repo to /repository/:org/:repo', () => {
    // Mock the repository API response for a valid repository
    cy.intercept('GET', '/api/v1/repository/user1/hello-world*', {
      statusCode: 200,
      body: mockRepository('user1', 'hello-world'),
    }).as('getRepo');

    // Visit shorthand URL
    cy.visit('/user1/hello-world');

    // Wait for redirect and API call
    cy.wait('@getRepo');

    // Verify URL was redirected to full repository path
    cy.location('pathname').should('eq', '/repository/user1/hello-world');

    // Verify repository page loaded correctly
    cy.get('[data-testid="repo-title"]').should('contain.text', 'hello-world');
  });

  it('redirects multi-segment repository names correctly', () => {
    // Mock the repository API response
    cy.intercept('GET', '/api/v1/repository/openshift/release/installer*', {
      statusCode: 200,
      body: mockRepository('openshift', 'release/installer', {
        description: 'OpenShift installer',
        can_write: false,
        can_admin: false,
      }),
    }).as('getRepo');

    // Visit shorthand URL with multi-segment repo name
    cy.visit('/openshift/release/installer');

    // Wait for redirect and API call
    cy.wait('@getRepo');

    // Verify URL was redirected correctly
    cy.location('pathname').should(
      'eq',
      '/repository/openshift/release/installer',
    );

    // Verify repository page loaded
    cy.get('[data-testid="repo-title"]').should(
      'contain.text',
      'release/installer',
    );
  });

  it('shows 404 error when repository does not exist', () => {
    // Mock 404 response from API
    cy.intercept('GET', '/api/v1/repository/nonexistent/repo*', {
      statusCode: 404,
      body: {
        error_message: 'Not Found',
        error_type: 'not_found',
      },
    }).as('getRepoNotFound');

    // Visit shorthand URL for non-existent repo
    cy.visit('/nonexistent/repo');

    // Wait for redirect and API call
    cy.wait('@getRepoNotFound');

    // Verify URL was redirected
    cy.location('pathname').should('eq', '/repository/nonexistent/repo');

    // Verify error message is displayed
    cy.contains('Unable to get repository').should('exist');
    cy.contains('HTTP404 - Not Found').should('exist');
  });

  it('does not redirect reserved route prefixes', () => {
    // Mock organization API response
    cy.intercept('GET', '/api/v1/organization/testorg', {
      statusCode: 404,
      body: {
        error_message: 'Not Found',
      },
    }).as('getOrg');

    // Visit /user/ path (reserved prefix)
    cy.visit('/user/testuser', {failOnStatusCode: false});

    // URL should NOT redirect to /repository/user/testuser
    cy.location('pathname').should('eq', '/user/testuser');

    // Should show organization component (existing behavior)
    cy.get('h1').should('contain.text', 'testuser');
  });

  it('redirects single-segment org URL to /organization/:org', () => {
    // Mock organization API response
    cy.intercept('GET', '/api/v1/organization/testorg', {
      statusCode: 200,
      body: {
        name: 'testorg',
        is_org_admin: false,
      },
    }).as('getOrg');

    // Visit shorthand organization URL
    cy.visit('/testorg');

    // Wait for redirect and API call
    cy.wait('@getOrg');

    // Verify URL was redirected to full organization path
    cy.location('pathname').should('eq', '/organization/testorg');

    // Verify organization page loaded
    cy.get('h1').should('contain.text', 'testorg');
  });

  it('shows error when organization does not exist', () => {
    // Mock 404 response from organization API
    cy.intercept('GET', '/api/v1/organization/nonexistentorg', {
      statusCode: 404,
      body: {
        error_message: 'Not Found',
      },
    }).as('getOrgNotFound');

    // Visit shorthand URL for non-existent organization
    cy.visit('/nonexistentorg');

    // Wait for redirect and API call
    cy.wait('@getOrgNotFound');

    // Verify URL was redirected to organization path
    cy.location('pathname').should('eq', '/organization/nonexistentorg');

    // Note: The organization page handles the 404, not the router
  });

  it('preserves query parameters for organization redirects', () => {
    // Mock organization API response
    cy.intercept('GET', '/api/v1/organization/testorg', {
      statusCode: 200,
      body: {
        name: 'testorg',
        is_org_admin: true,
      },
    }).as('getOrg');

    // Visit shorthand organization URL with query parameter
    cy.visit('/testorg?tab=teams');

    // Wait for redirect and API call
    cy.wait('@getOrg');

    // Verify URL was redirected with query parameter preserved
    cy.location('pathname').should('eq', '/organization/testorg');
    cy.location('search').should('eq', '?tab=teams');
  });

  it('preserves hash fragments for organization redirects', () => {
    // Mock organization API response
    cy.intercept('GET', '/api/v1/organization/testorg', {
      statusCode: 200,
      body: {
        name: 'testorg',
        is_org_admin: true,
      },
    }).as('getOrg');

    // Visit shorthand organization URL with hash fragment
    cy.visit('/testorg#section');

    // Wait for redirect and API call
    cy.wait('@getOrg');

    // Verify URL was redirected with hash fragment preserved
    cy.location('pathname').should('eq', '/organization/testorg');
    cy.location('hash').should('eq', '#section');
  });

  it('preserves query parameters during redirect', () => {
    // Mock the repository API response
    cy.intercept('GET', '/api/v1/repository/user1/hello-world*', {
      statusCode: 200,
      body: mockRepository('user1', 'hello-world'),
    }).as('getRepo');

    // Visit shorthand URL with query parameter
    cy.visit('/user1/hello-world?tab=tags');

    // Wait for redirect
    cy.wait('@getRepo');

    // Verify URL was redirected with query parameter preserved
    cy.location('pathname').should('eq', '/repository/user1/hello-world');
    cy.location('search').should('eq', '?tab=tags');

    // Verify the Tags tab is active
    cy.get('[role="tab"][aria-selected="true"]').should('contain.text', 'Tags');
  });

  it('preserves hash fragments during redirect', () => {
    // Mock the repository API response
    cy.intercept('GET', '/api/v1/repository/user1/hello-world*', {
      statusCode: 200,
      body: mockRepository('user1', 'hello-world'),
    }).as('getRepo');

    // Visit shorthand URL with hash fragment
    cy.visit('/user1/hello-world#section');

    // Wait for redirect
    cy.wait('@getRepo');

    // Verify URL was redirected with hash fragment preserved
    cy.location('pathname').should('eq', '/repository/user1/hello-world');
    cy.location('hash').should('eq', '#section');
  });

  it('preserves both query parameters and hash fragments during redirect', () => {
    // Mock the repository API response
    cy.intercept('GET', '/api/v1/repository/user1/hello-world*', {
      statusCode: 200,
      body: mockRepository('user1', 'hello-world'),
    }).as('getRepo');

    // Visit shorthand URL with both query parameter and hash fragment
    cy.visit('/user1/hello-world?tab=tags#section');

    // Wait for redirect
    cy.wait('@getRepo');

    // Verify URL was redirected with both query parameter and hash preserved
    cy.location('pathname').should('eq', '/repository/user1/hello-world');
    cy.location('search').should('eq', '?tab=tags');
    cy.location('hash').should('eq', '#section');

    // Verify the Tags tab is active
    cy.get('[role="tab"][aria-selected="true"]').should('contain.text', 'Tags');
  });
});
