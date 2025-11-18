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
    // Add API mocks before visiting
    cy.fixture('config.json').then((config) => {
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    cy.visit('/organization');
    cy.wait('@getConfig'); // Wait for config to load

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
    cy.contains('Permanently delete selected items?');
    cy.contains(
      'This action deletes all selected items and cannot be recovered.',
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
    cy.contains('Permanently delete selected items?');
    cy.contains(
      'This action deletes all selected items and cannot be recovered.',
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

  it('Shows user orgs when superuser API fails', () => {
    // Setup superuser with feature flags enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock superuser with user's own organizations
    cy.fixture('superuser.json').then((user) => {
      cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
    });

    // Simulate superuser API endpoints returning 403 (fresh login required)
    cy.intercept('GET', '/api/v1/superuser/organizations/', {
      statusCode: 403,
      body: {error: 'Fresh login required'},
    }).as('getSuperuserOrganizationsFailed');

    cy.intercept('GET', '/api/v1/superuser/users/', {
      statusCode: 403,
      body: {error: 'Fresh login required'},
    }).as('getSuperuserUsersFailed');

    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.wait('@getSuperUser');
    cy.wait('@getSuperuserOrganizationsFailed');
    cy.wait('@getSuperuserUsersFailed');

    // Should still show user's own organizations from /api/v1/user/
    cy.contains('testorg').should('exist');
    cy.contains('superuser').should('exist');

    // Verify the organization is clickable
    cy.contains('testorg').should('be.visible');
  });

  it('Shows combined orgs for superuser when API succeeds', () => {
    // Setup superuser with feature flags enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock superuser with user's own organizations (only testorg)
    cy.fixture('superuser.json').then((user) => {
      cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
    });

    // Mock successful superuser API calls with additional orgs
    cy.fixture('superuser-organizations.json').then((orgsData) => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
        'getSuperuserOrganizations',
      );
    });

    cy.fixture('superuser-users.json').then((usersData) => {
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

    // Should show user's own org (testorg)
    cy.contains('testorg').should('exist');

    // Should also show additional orgs from superuser API
    cy.contains('projectquay').should('exist');
    cy.contains('coreos').should('exist');

    // Should show current user
    cy.contains('superuser').should('exist');
  });

  it('Shows no duplicates when user org appears in superuser API', () => {
    // Setup superuser
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    cy.fixture('superuser.json').then((user) => {
      cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
    });

    // Superuser API includes testorg (which user is also a member of)
    cy.fixture('superuser-organizations.json').then((orgsData) => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
        'getSuperuserOrganizations',
      );
    });

    cy.fixture('superuser-users.json').then((usersData) => {
      cy.intercept('GET', '/api/v1/superuser/users/', usersData).as(
        'getSuperuserUsers',
      );
    });

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

    // Count how many times testorg appears - should be exactly once
    cy.get('td[data-label="Name"]')
      .contains('testorg')
      .parents('tr')
      .should('have.length', 1);
  });

  it('Read-only superuser can see all organizations and users', () => {
    // Mock config with superuser features enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock read-only superuser (global_readonly_super_user = true)
    cy.fixture('superuser.json').then((user) => {
      user.global_readonly_super_user = true;
      user.super_user = false; // Regular superuser flag is false
      cy.intercept('GET', '/api/v1/user/', user).as('getReadOnlySuperUser');
    });

    // Mock successful superuser API calls
    cy.fixture('superuser-organizations.json').then((orgsData) => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
        'getSuperuserOrganizations',
      );
    });

    cy.fixture('superuser-users.json').then((usersData) => {
      cy.intercept('GET', '/api/v1/superuser/users/', usersData).as(
        'getSuperuserUsers',
      );
    });

    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.wait('@getReadOnlySuperUser');
    cy.wait('@getSuperuserOrganizations');
    cy.wait('@getSuperuserUsers');

    // Should show user's own org (testorg)
    cy.contains('testorg').should('exist');

    // Should show additional orgs from superuser API (same as regular superuser)
    cy.contains('projectquay').should('exist');
    cy.contains('coreos').should('exist');

    // Should show current user
    cy.contains('superuser').should('exist');

    // Should show other users from superuser API
    cy.contains('user1').should('exist');
  });

  it('Read-only superuser cannot perform actions (no kebab menus)', () => {
    // Mock config with superuser features enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock read-only superuser
    cy.fixture('superuser.json').then((user) => {
      user.global_readonly_super_user = true;
      user.super_user = false;
      cy.intercept('GET', '/api/v1/user/', user).as('getReadOnlySuperUser');
    });

    // Mock superuser API calls
    cy.fixture('superuser-organizations.json').then((orgsData) => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
        'getSuperuserOrganizations',
      );
    });

    cy.fixture('superuser-users.json').then((usersData) => {
      cy.intercept('GET', '/api/v1/superuser/users/', usersData).as(
        'getSuperuserUsers',
      );
    });

    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.wait('@getReadOnlySuperUser');
    cy.wait('@getSuperuserOrganizations');
    cy.wait('@getSuperuserUsers');

    // Settings column header should NOT be visible for read-only superusers
    cy.contains('th', 'Settings').should('not.exist');

    // No kebab menus should be visible (canModify = false for read-only superuser)
    cy.get('[data-testid$="-options-toggle"]').should('not.exist');

    // Create Organization button SHOULD exist (regular user action, not superuser action)
    cy.get('#create-organization-button').should('exist');

    // Create User button should NOT exist (superuser-only action)
    cy.get('[data-testid="create-user-button"]').should('not.exist');
  });

  it('Read-only superuser cannot select orgs/users they do not own', () => {
    // Mock config with superuser features enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock read-only superuser with their own org (testorg)
    cy.fixture('superuser.json').then((user) => {
      user.global_readonly_super_user = true;
      user.super_user = false;
      cy.intercept('GET', '/api/v1/user/', user).as('getReadOnlySuperUser');
    });

    // Mock superuser API calls with additional orgs
    cy.fixture('superuser-organizations.json').then((orgsData) => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
        'getSuperuserOrganizations',
      );
    });

    cy.fixture('superuser-users.json').then((usersData) => {
      cy.intercept('GET', '/api/v1/superuser/users/', usersData).as(
        'getSuperuserUsers',
      );
    });

    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.wait('@getReadOnlySuperUser');
    cy.wait('@getSuperuserOrganizations');
    cy.wait('@getSuperuserUsers');

    // Verify Settings column header does NOT exist for read-only superusers
    cy.contains('th', 'Settings').should('not.exist');

    // Find the row for 'testorg' (org the readonly user owns)
    cy.contains('a', 'testorg')
      .parents('tr')
      .within(() => {
        // Should have a checkbox (can delete own org)
        cy.get('input[type="checkbox"]').should('exist');
      });

    // Find the row for 'projectquay' (org from superuser endpoint, not owned)
    cy.contains('a', 'projectquay')
      .parents('tr')
      .within(() => {
        // Should NOT have a checkbox (cannot delete other's org)
        cy.get('input[type="checkbox"]').should('not.exist');
      });

    // Find the row for current user 'superuser'
    cy.contains('a', 'superuser')
      .parents('tr')
      .within(() => {
        // Should have a checkbox (can delete own user account)
        cy.get('input[type="checkbox"]').should('exist');
      });

    // Find the row for other user 'user1'
    cy.contains('a', 'user1')
      .parents('tr')
      .within(() => {
        // Should NOT have a checkbox (cannot delete other users)
        cy.get('input[type="checkbox"]').should('not.exist');
      });
  });
});
