/// <reference types="cypress" />

describe('Signin page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
  });

  it('Succesful signin', () => {
    cy.visit(`/signin`);
    // Wait for page to fully load and CSRF token to initialize
    cy.get('button[type=submit]').should('be.visible');
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();
    cy.url().should('include', '/organization');
    cy.get('#create-organization-button').should('be.visible');
  });
});
