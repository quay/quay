/// <reference types="cypress" />

describe('Org List Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Search Filter', () => {
    cy.visit('/organization');

    // Filter for a single org
    cy.get('#orgslist-search-input').type('user1');
    cy.contains('1 - 1 of 1');
    cy.get('[aria-label="Reset search"]').click();

    // Filter for a non-existent org
    cy.get('#orgslist-search-input').type('asdf');
    cy.contains('0 - 0 of 0');
    cy.get('[aria-label="Reset search"]').click();
  });

  it('Search by name via regex', () => {
    cy.visit('/organization');
    cy.get('[id="filter-input-advanced-search"]').should('not.exist');
    cy.get('[aria-label="Open advanced search"]').click();
    cy.get('[id="filter-input-advanced-search"]').should('be.visible');
    cy.get('[id="filter-input-regex-checker"]').click();
    cy.get('#orgslist-search-input').type('^co');
    cy.contains('coreos').should('exist');
    cy.contains('calico').should('not.exist');
    cy.get('[aria-label="Reset search"]').click();
    cy.contains('coreos').should('exist');
    cy.contains('calico').should('exist');
  });

  it('Create Org', () => {
    cy.intercept('/organization').as('getOrganization');
    cy.visit('/organization');
    cy.wait('@getOrganization');

    // Open and cancel modal
    cy.get('#create-organization-button').click();
    cy.get('#create-org-cancel').click();

    // Create Org
    cy.get('#create-organization-button').click();
    cy.get('#create-org-name-input').type('cypress');
    cy.get('#create-org-email-input').type('cypress@redhat.com');
    cy.get('#create-org-confirm').click({timeout: 10000});

    cy.get('#orgslist-search-input').type('cypress');
    cy.contains('1 - 1 of 1');

    // Validate all required fields are populated
    cy.get('#create-organization-button').click();
    cy.get('#create-org-confirm').should('be.disabled');

    // Valid org name
    cy.get('#create-org-name-input').type('cypress');
    cy.get('#create-org-confirm').should('be.disabled');

    // Valid email address
    cy.get('#create-org-email-input').type('cypress');
    cy.get('#create-org-name-input').click();
    cy.contains('Enter a valid email: email@provider.com');
    cy.get('#create-org-confirm').should('be.disabled');
    cy.get('#create-org-cancel').click();
  });

  it('Delete Org', () => {
    cy.visit('/organization');

    // Open the select box and check delete for all orgs, don't actually delete
    cy.get('button[id="toolbar-dropdown-checkbox"]').click();
    cy.contains('Select page').click();
    cy.contains('Actions').click();
    cy.contains('Delete').click();
    cy.contains('Permanently delete organizations?');
    cy.contains(
      'This action deletes all organizations and cannot be recovered.',
    );
    cy.contains('Confirm deletion by typing "confirm" below:');
    cy.get('#delete-org-cancel').click();

    // Delete single org
    cy.get('#orgslist-search-input').type('projectquay');
    cy.contains('1 - 1 of 1');
    cy.get('button[id="toolbar-dropdown-checkbox"]').click();
    cy.contains('Select page').click();
    cy.contains('Actions').click();
    cy.contains('Delete').click();
    cy.contains('Permanently delete organizations?');
    cy.contains(
      'This action deletes all organizations and cannot be recovered.',
    );
    cy.contains('Confirm deletion by typing "confirm" below:');
    cy.get('input[id="delete-confirmation-input"]').type('confirm');
    cy.get('[id="bulk-delete-modal"]')
      .within(() => cy.get('button:contains("Delete")').click())
      .then(() => {
        cy.get('[aria-label="Reset search"]').click();
        cy.get('#orgslist-search-input').type('projectquay');
        cy.contains('0 - 0 of 0');
      });
  });

  it('Pagination', () => {
    cy.visit('/organization');

    cy.contains('1 - 20 of 30').should('exist');
    cy.get('td[data-label="Name"]').should('have.length', 20);

    // cycle through the pages
    cy.get('button[aria-label="Go to next page"]').first().click();
    cy.get('td[data-label="Name"]').should('have.length', 10);

    // Go to first page
    cy.get('button[aria-label="Go to first page"]').first().click();
    cy.contains('unleash').should('exist');
    cy.get('td[data-label="Name"]').should('have.length', 20);

    // Go to last page
    cy.get('button[aria-label="Go to last page"]').first().click();
    cy.contains('user1').should('exist');
    cy.get('td[data-label="Name"]').should('have.length', 10);

    // Change per page
    cy.get('button:contains("21 - 30 of 30")').first().click();
    cy.contains('20 per page').click();
    cy.get('td[data-label="Name"]').should('have.length', 20);
    cy.contains('1 - 20 of 30').should('exist');
  });

  it('Superuser displays quota consumed column (PROJQUAY-9641)', () => {
    // This test verifies that superusers can see quota consumed data
    // for organizations and user namespaces in the organizations list

    // Mock config with quota features enabled
    cy.fixture('config.json').then((config) => {
      config.features.QUOTA_MANAGEMENT = true;
      config.features.EDIT_QUOTA = true;
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock superuser
    cy.fixture('superuser.json').then((user) => {
      cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
    });

    // Mock superuser organizations with quota_report data
    cy.fixture('superuser-organizations.json').then((orgsData) => {
      // Add quota_report to organizations
      orgsData.organizations[0].quota_report = {
        quota_bytes: 10737418240,
        configured_quota: 53687091200,
      };
      orgsData.organizations[1].quota_report = {
        quota_bytes: 5368709120,
        configured_quota: 21474836480,
      };
      cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
        'getSuperuserOrganizations',
      );
    });

    // Mock superuser users with quota_report data
    cy.fixture('superuser-users.json').then((usersData) => {
      // Add quota_report to users
      usersData.users[0].quota_report = {
        quota_bytes: 2147483648,
        configured_quota: 10737418240,
      };
      cy.intercept('GET', '/api/v1/superuser/users/', usersData).as(
        'getSuperuserUsers',
      );
    });

    // Mock organization details
    cy.intercept('GET', '/api/v1/organization/testorg', {
      statusCode: 200,
      body: {
        name: 'testorg',
        email: 'testorg@example.com',
        teams: {owners: 'admin'},
      },
    });

    cy.intercept('GET', '/api/v1/organization/projectquay', {
      statusCode: 200,
      body: {
        name: 'projectquay',
        email: 'projectquay@example.com',
        teams: {},
      },
    });

    cy.intercept('GET', '/api/v1/organization/coreos', {
      statusCode: 200,
      body: {
        name: 'coreos',
        email: 'coreos@example.com',
        teams: {owners: 'admin'},
      },
    });

    // Mock robots/members/repositories for all organizations
    cy.intercept('GET', '/api/v1/organization/*/robots', {
      statusCode: 200,
      body: {robots: []},
    });

    cy.intercept('GET', '/api/v1/organization/*/members', {
      statusCode: 200,
      body: {members: []},
    });

    cy.intercept('GET', '/api/v1/repository?namespace=*', {
      statusCode: 200,
      body: {repositories: []},
    });

    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.wait('@getSuperUser');
    cy.wait('@getSuperuserOrganizations');
    cy.wait('@getSuperuserUsers');

    // Verify the Size column header exists for superusers
    cy.contains('th', 'Size').should('exist');

    // Verify quota data cells are visible and contain actual data
    cy.get('td[data-label="Size"]').should('exist');

    // Verify at least one organization shows quota consumed data (not "—")
    // The quota should be displayed as "10.0 GiB / 50.0 GiB" format
    cy.get('td[data-label="Size"]').first().should('not.contain.text', '—');
  });

  it('Superuser displays user status labels', () => {
    // Mock config with superuser features enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock superuser
    cy.fixture('superuser.json').then((user) => {
      cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
    });

    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.wait('@getSuperUser');

    cy.get('#orgslist-search-input').type('user1');

    cy.contains('a', 'user1')
      .parents('tr')
      .within(() => {
        cy.contains('Superuser').should('exist');
      });
  });
});
