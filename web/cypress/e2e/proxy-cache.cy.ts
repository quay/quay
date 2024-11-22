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
  });

  const createProxyCacheConfig = (cy) => {
    cy.get('[data-testid="remote-registry-input"]').type('docker.io');
    cy.get('[data-testid="save-proxy-cache-btn"]').click();
  };

  it('can create proxy cache configuration for an organization', () => {
    cy.visit('/organization/projectquay?tab=Settings');
    cy.contains('Proxy-Cache config').click();
    createProxyCacheConfig(cy);
    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully configured proxy cache')
      .should('exist');
  });

  it('can delete proxy cache configuration for an organization', () => {
    cy.visit('/organization/projectquay?tab=Settings');
    cy.contains('Proxy-Cache config').click();
    createProxyCacheConfig(cy);
    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully configured proxy cache')
      .should('exist');
    cy.get('[data-testid="delete-proxy-cache-btn"]').click();
    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully deleted proxy cache configuration')
      .should('exist');
  });
});
