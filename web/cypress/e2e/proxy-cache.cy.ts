/// <reference types="cypress" />

describe('Organization settings - Proxy-cache configuration', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');

    // Intercept the /validateproxycache API call
    cy.intercept('POST', '/api/v1/organization/*/validateproxycache', (req) => {
      const {upstream_registry_username, upstream_registry_password} = req.body;
      if (upstream_registry_username && upstream_registry_password) {
        req.reply({
          statusCode: 202,
          body: 'Valid',
        });
      } else {
        req.reply({
          statusCode: 202,
          body: 'Anonymous',
        });
      }
    }).as('validateProxyCache');

    // Intercept the /proxycache API call
    cy.intercept('POST', '/api/v1/organization/*/proxycache', {
      statusCode: 201,
      body: 'Created',
    }).as('createProxyCache');
  });

  const createAnonymousProxyCacheConfig = (cy) => {
    cy.get('[data-testid="remote-registry-input"]').type('docker.io');
    cy.get('[data-testid="save-proxy-cache-btn"]').click();
  };

  it('can create anonymous proxy cache configuration for an organization', () => {
    cy.visit('/organization/projectquay?tab=Settings');
    cy.get('[data-testid="Proxy Cache"]').click();
    createAnonymousProxyCacheConfig(cy);

    // Wait for the validateproxycache API call and assert the response
    cy.wait('@validateProxyCache').then((interception) => {
      expect(interception.response?.statusCode).to.eq(202);
      expect(interception.response?.body).to.eq('Anonymous');
    });

    // Wait for the proxycache API call and assert the response
    cy.wait('@createProxyCache').then((interception) => {
      expect(interception.response?.statusCode).to.eq(201);
      expect(interception.response?.body).to.eq('Created');
    });

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully configured proxy cache')
      .should('exist');
  });

  it('can create proxy cache configuration with registry credentials for an organization', () => {
    cy.visit('/organization/projectquay?tab=Settings');
    cy.get('[data-testid="Proxy Cache"]').click();

    cy.get('[data-testid="remote-registry-input"]').type('docker.io');
    cy.get('[data-testid="remote-registry-username"]').type('testuser1');
    cy.get('[data-testid="remote-registry-password"]').type('testpass');
    cy.get('[data-testid="remote-registry-expiration"]').clear().type('76400');
    cy.get('[data-testid="remote-registry-insecure"]').check();

    cy.get('[data-testid="save-proxy-cache-btn"]').click();

    // Wait for the validateproxycache API call and assert the response
    cy.wait('@validateProxyCache').then((interception) => {
      expect(interception.response?.statusCode).to.eq(202);
      expect(interception.response?.body).to.eq('Valid');
    });

    // Wait for the proxycache API call and assert the response
    cy.wait('@createProxyCache').then((interception) => {
      expect(interception.response?.statusCode).to.eq(201);
      expect(interception.response?.body).to.eq('Created');
    });

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully configured proxy cache')
      .should('exist');
  });

  it('can delete proxy cache configuration for an organization', () => {
    cy.visit('/organization/prometheus?tab=Settings');
    cy.get('[data-testid="Proxy Cache"]').click();

    cy.get('[data-testid="delete-proxy-cache-btn"]').click();
    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully deleted proxy cache configuration')
      .should('exist');
  });

  it('proxy cache config is not shown for user organization', () => {
    cy.visit('/organization/user1?tab=Settings');
    cy.get('[data-testid="Proxy Cache"]').should('not.exist');
  });
});
