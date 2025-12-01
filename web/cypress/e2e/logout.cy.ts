/// <reference types="cypress" />

describe('Logout functionality', () => {
  before(() => {
    cy.exec('npm run quay:seed');
  });

  beforeEach(() => {
    // Login using the actual backend (not mocks)
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });

    // Visit the organization page (where a logged-in user would be)
    cy.visit('/organization');

    // Verify we stayed on /organization (not redirected to signin)
    cy.url({timeout: 30000}).should('include', '/organization');

    // Wait for the page to load and user menu to be visible (confirms we're logged in)
    cy.get('#user-menu-toggle', {timeout: 10000}).should('be.visible');
  });

  it('Successfully logs out when API call succeeds', () => {
    // Mock successful logout
    cy.intercept('POST', '/api/v1/signout', {
      statusCode: 200,
      body: {success: true},
    }).as('logoutSuccess');

    // Click user menu
    cy.get('#user-menu-toggle').click();

    // Click logout
    cy.contains('Logout').click();

    // Verify API was called
    cy.wait('@logoutSuccess');

    // Should redirect to signin page
    cy.url().should('include', '/signin');
  });

  it('Redirects to signin page even when logout API fails with network error', () => {
    // Mock network error for logout
    cy.intercept('POST', '/api/v1/signout', {
      forceNetworkError: true,
    }).as('logoutNetworkError');

    // Click user menu
    cy.get('#user-menu-toggle').click();

    // Click logout
    cy.contains('Logout').click();

    // Wait for API call to fail
    cy.wait('@logoutNetworkError');

    // Should STILL redirect to signin page despite network error
    cy.url().should('include', '/signin');

    // Should NOT show error modal
    cy.contains('Unable to log out').should('not.exist');
  });

  it('Redirects to signin page even when logout API returns 500 error', () => {
    // Mock server error for logout
    cy.intercept('POST', '/api/v1/signout', {
      statusCode: 500,
      body: {message: 'Internal server error'},
    }).as('logoutServerError');

    // Click user menu
    cy.get('#user-menu-toggle').click();

    // Click logout
    cy.contains('Logout').click();

    // Wait for API call to fail
    cy.wait('@logoutServerError');

    // Should STILL redirect to signin page despite server error
    cy.url().should('include', '/signin');

    // Should NOT show error modal
    cy.contains('Unable to log out').should('not.exist');
  });

  it('Redirects to signin page even when logout API is slow', () => {
    // Mock slow logout API response (1 second delay)
    cy.intercept('POST', '/api/v1/signout', (req) => {
      req.reply({
        delay: 1000, // 1 second delay
        statusCode: 200,
        body: {success: true},
      });
    }).as('logoutSlow');

    // Click user menu
    cy.get('#user-menu-toggle').click();

    // Click logout
    cy.contains('Logout').click();

    // Should redirect to signin page after API completes (within 5 seconds)
    // The finally block executes after the 1 second delay
    cy.url({timeout: 5000}).should('include', '/signin');

    // Verify we're on signin page with login form visible
    cy.get('#pf-login-username-id').should('be.visible');

    // Should NOT show error modal
    cy.contains('Unable to log out').should('not.exist');
  });

  it('Clears user session state on logout', () => {
    // Click user menu
    cy.get('#user-menu-toggle').click();

    // Click logout
    cy.contains('Logout').click();

    // Should be on signin page (finally block redirects immediately)
    cy.url({timeout: 10000}).should('include', '/signin');

    // Verify login form is visible
    cy.get('#pf-login-username-id').should('be.visible');

    // Try to navigate back to a protected page
    cy.visit('/organization/user1');

    // Should redirect to signin (not authenticated) or stay on signin
    cy.url({timeout: 10000}).should('include', '/signin');

    // Verify still on login page
    cy.get('#pf-login-username-id').should('be.visible');
  });

  it('Logout button is accessible from user menu', () => {
    // Click user menu
    cy.get('#user-menu-toggle').click();

    // Verify logout menu item exists and is visible
    cy.contains('Logout').should('be.visible');

    // Verify logout menu item has danger styling (red text)
    cy.contains('Logout')
      .parent()
      .should('have.attr', 'class')
      .and('include', 'pf-m-danger');
  });
});
