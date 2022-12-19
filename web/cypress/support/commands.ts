/// <reference types="cypress" />

// Namespace must be declared to add functions when using TS
// eslint-disable-next-line @typescript-eslint/no-namespace
declare namespace Cypress {
  interface Chainable {
    loginByCSRF: (arg: string) => void;
  }
}

const username = 'user1';
const password = 'password';
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
