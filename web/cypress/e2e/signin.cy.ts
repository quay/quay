/// <reference types="cypress" />

describe('Signin page', () => {
  // FIXME: the test fails on CI, see https://issues.redhat.com/browse/PROJQUAY-5448
  it.skip('Succesful signin', () => {
    cy.visit(`/signin`);
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();
    cy.url().should('include', '/organization');
  });
});
