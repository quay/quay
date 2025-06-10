/// <reference types="cypress" />

describe('Notification Drawer', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/api/v1/user/notifications', {
      fixture: 'notifications.json',
    }).as('getNotifications');
    cy.intercept('GET', '/organization').as('getOrganization');
    cy.visit('/organization');
    cy.wait('@getOrganization');
  });

  it('displays notification bell in header', () => {
    cy.get('[data-testid="notification-bell"]').should('exist');
  });

  it('opens notification drawer when bell is clicked', () => {
    cy.get('[data-testid="notification-bell"]').click();
    cy.get('[data-testid="notification-drawer"]').should('be.visible');
  });

  it('displays notifications in drawer', () => {
    cy.get('[data-testid="notification-bell"]').click();
    cy.get('[data-testid="notification-drawer"]').within(() => {
      cy.get('[data-testid="notification-item"]').should('have.length', 2);
    });
  });

  it('marks notification as read when clicked', () => {
    cy.get('[data-testid="notification-bell"]').click();
    // Click the first notification header
    cy.get('[data-testid="notification-item"]')
      .first()
      .find('[data-testid="notification-header"]')
      .click();
    cy.get('[data-testid="notification-item"]')
      .first()
      .should('have.class', 'pf-m-read');
  });

  it('deletes notification when delete button is clicked', () => {
    cy.get('[data-testid="notification-bell"]').click();
    cy.intercept('PUT', '/api/v1/user/notifications/*', {
      statusCode: 200,
      body: {dismissed: true},
    }).as('dismissNotification');
    cy.fixture('notifications.json').then((notifications) => {
      // Remove the first notification to simulate deletion
      const remainingNotifications = {
        notifications: notifications.notifications.slice(1),
        additional: false,
      };
      cy.intercept('GET', '/api/v1/user/notifications', {
        statusCode: 200,
        body: remainingNotifications,
      }).as('getNotifications');
    });
    cy.get('[data-testid="notification-item"]')
      .first()
      .find('[data-testid="delete-notification"]')
      .click();
    cy.wait('@dismissNotification');
    cy.wait('@getNotifications');
    cy.get('[data-testid="notification-item"]').should('have.length', 1);
  });
});
