/// <reference types="cypress" />

describe('Footer Component', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Displays footer with version and documentation link', () => {
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');

    cy.visit('/organization');
    cy.wait('@getConfig');

    // Check footer exists
    cy.get('.quay-footer').should('exist');

    // Check documentation link
    cy.get('.quay-footer-link')
      .should('have.attr', 'href', 'https://docs.projectquay.io/')
      .should('have.attr', 'target', '_blank')
      .should('contain.text', 'Documentation');

    // Check version is displayed
    cy.get('.quay-footer-version').should('contain.text', 'Quay 3.15.3');
  });
});
