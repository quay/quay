/// <reference types="cypress" />

describe('Global Readonly Superuser - Organizations List', () => {
  beforeEach(() => {
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('should display all organizations for global readonly superusers', () => {
    // Mock config with superuser features enabled
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['SUPERUSERS_FULL_ACCESS'] = true;
        res.body.features['SUPER_USERS'] = true;
        return res;
      }),
    ).as('getConfig');

    // Mock user as global readonly superuser (not regular superuser)
    cy.intercept('GET', '/api/v1/user/', (req) =>
      req.reply((res) => {
        res.body.super_user = false; // Not a regular superuser
        res.body.is_global_readonly_superuser = true; // But is global readonly
        res.body.username = 'readonly_admin';
        res.body.organizations = [
          {name: 'user_org', is_org_admin: true}, // User's own org
        ];
        return res;
      }),
    ).as('getUser');

    // Mock superuser organizations endpoint - returns ALL organizations
    cy.intercept('GET', '/api/v1/superuser/organizations/', {
      organizations: [
        {name: 'org1', email: 'org1@example.com'},
        {name: 'org2', email: 'org2@example.com'},
        {name: 'org3', email: 'org3@example.com'},
        {name: 'testorg', email: 'test@example.com'},
      ],
    }).as('getSuperuserOrgs');

    // Mock superuser users endpoint
    cy.intercept('GET', '/api/v1/superuser/users/', {
      users: [
        {username: 'user1', email: 'user1@example.com', enabled: true},
        {username: 'user2', email: 'user2@example.com', enabled: true},
        {
          username: 'readonly_admin',
          email: 'readonly@example.com',
          enabled: true,
        },
      ],
    }).as('getSuperuserUsers');

    cy.visit('/organization');

    cy.wait('@getConfig');
    cy.wait('@getUser');
    cy.wait('@getSuperuserOrgs');
    cy.wait('@getSuperuserUsers');

    // Verify ALL organizations are displayed (from superuser endpoint)
    cy.contains('org1').should('exist');
    cy.contains('org2').should('exist');
    cy.contains('org3').should('exist');
    cy.contains('testorg').should('exist');

    // Verify users are also displayed
    cy.contains('user1').should('exist');
    cy.contains('user2').should('exist');
    cy.contains('readonly_admin').should('exist');

    // Verify we have more organizations than just the user's own
    cy.get('table tbody tr').should('have.length.greaterThan', 1);
  });

  it('should NOT display superuser organizations without is_global_readonly_superuser flag', () => {
    // Mock config with superuser features enabled
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['SUPERUSERS_FULL_ACCESS'] = true;
        res.body.features['SUPER_USERS'] = true;
        return res;
      }),
    ).as('getConfig');

    // Mock user as regular user (not superuser, not global readonly)
    cy.intercept('GET', '/api/v1/user/', (req) =>
      req.reply((res) => {
        res.body.super_user = false;
        res.body.is_global_readonly_superuser = false; // Not global readonly
        res.body.username = 'regular_user';
        res.body.organizations = [
          {name: 'user_org', is_org_admin: true}, // User's own org only
        ];
        return res;
      }),
    ).as('getUser');

    // These endpoints should NOT be called for regular users
    cy.intercept('GET', '/api/v1/superuser/organizations/', {
      statusCode: 403,
      body: {error: 'Unauthorized'},
    }).as('getSuperuserOrgs');

    cy.intercept('GET', '/api/v1/superuser/users/', {
      statusCode: 403,
      body: {error: 'Unauthorized'},
    }).as('getSuperuserUsers');

    cy.visit('/organization');

    cy.wait('@getConfig');
    cy.wait('@getUser');

    // Superuser endpoints should NOT be called
    cy.get('@getSuperuserOrgs.all').should('have.length', 0);
    cy.get('@getSuperuserUsers.all').should('have.length', 0);

    // Should only see user's own organization and their own username
    cy.contains('user_org').should('exist');
    cy.contains('regular_user').should('exist');

    // Should have exactly 2 rows (user's org + user's namespace)
    cy.get('table tbody tr').should('have.length', 2);
  });

  it('should display all organizations for regular superusers', () => {
    // Mock config with superuser features enabled
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['SUPERUSERS_FULL_ACCESS'] = true;
        res.body.features['SUPER_USERS'] = true;
        return res;
      }),
    ).as('getConfig');

    // Mock user as regular superuser
    cy.intercept('GET', '/api/v1/user/', (req) =>
      req.reply((res) => {
        res.body.super_user = true; // Regular superuser
        res.body.is_global_readonly_superuser = false;
        res.body.username = 'admin';
        res.body.organizations = [{name: 'admin_org', is_org_admin: true}];
        return res;
      }),
    ).as('getUser');

    // Mock superuser organizations endpoint
    cy.intercept('GET', '/api/v1/superuser/organizations/', {
      organizations: [
        {name: 'org1', email: 'org1@example.com'},
        {name: 'org2', email: 'org2@example.com'},
      ],
    }).as('getSuperuserOrgs');

    // Mock superuser users endpoint
    cy.intercept('GET', '/api/v1/superuser/users/', {
      users: [
        {username: 'user1', email: 'user1@example.com', enabled: true},
        {username: 'admin', email: 'admin@example.com', enabled: true},
      ],
    }).as('getSuperuserUsers');

    cy.visit('/organization');

    cy.wait('@getConfig');
    cy.wait('@getUser');
    cy.wait('@getSuperuserOrgs');
    cy.wait('@getSuperuserUsers');

    // Verify organizations are displayed
    cy.contains('org1').should('exist');
    cy.contains('org2').should('exist');
    cy.contains('user1').should('exist');
  });
});
