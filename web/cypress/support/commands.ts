/// <reference types="cypress" />

// Namespace must be declared to add functions when using TS
// eslint-disable-next-line @typescript-eslint/no-namespace
declare namespace Cypress {
  interface Chainable {
    login: () => void;
    loginByCSRF: (arg: string) => void;
    getIframeBody: (selector: string) => Cypress.Chainable<JQuery<any>>;
  }
}

const username = 'user1';
const password = 'password';

// Session-based login command - caches session across tests
Cypress.Commands.add('login', () => {
  cy.session(
    username,
    () => {
      // Get CSRF token first
      cy.request(
        'GET',
        `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`,
      ).then((response) => {
        const csrfToken = response.body.csrf_token;
        // Perform login
        cy.request({
          method: 'POST',
          url: `${Cypress.env('REACT_QUAY_APP_API_URL')}/api/v1/signin`,
          headers: {
            'X-CSRF-Token': csrfToken,
          },
          body: {
            username,
            password,
          },
        }).then((resp) => {
          expect(resp.status).to.eq(200);
        });
      });
    },
    {
      validate: () => {
        // Validate session is still valid
        cy.request({
          url: `${Cypress.env('REACT_QUAY_APP_API_URL')}/api/v1/user/`,
          failOnStatusCode: false,
        })
          .its('status')
          .should('eq', 200);
      },
    },
  );
});

// Legacy login command - kept for backwards compatibility
Cypress.Commands.add('loginByCSRF', (csrfToken) => {
  cy.request({
    method: 'POST',
    url: `${Cypress.env('REACT_QUAY_APP_API_URL')}/api/v1/signin`,
    failOnStatusCode: false, // dont fail so we can make assertions
    headers: {
      'X-CSRF-Token': csrfToken,
    },
    body: {
      username: username,
      password: password,
    },
  });
});

// Used for adding iframes to the scope of cy
Cypress.Commands.add('getIframeBody', (selector: string) => {
  cy.log('getIframeBody');
  return cy
    .get(selector, {log: false})
    .its('0.contentDocument.body', {log: false})
    .should('not.be.empty')
    .then((body) => cy.wrap(body, {log: false}));
});
