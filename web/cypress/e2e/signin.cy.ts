/// <reference types="cypress" />

describe('Signin page', () => {
  it('Succesful signin', () => {
    cy.visit(`/signin`);
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();
    cy.url().should('include', '/organization');
  });
});
