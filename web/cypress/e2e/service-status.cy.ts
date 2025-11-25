/// <reference types="cypress" />
import {formatDate} from '../../src/libs/utils';

describe('Default permissions page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.fixture('config.json').then((config) => {
      config.features.BILLING = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Intercept external StatusPage script to prevent actual network requests
    cy.intercept('GET', '**/cdn.statuspage.io/**', {
      statusCode: 200,
      body: '// Mock StatusPage script',
    }).as('getStatuspageScript');

    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Displays incidents and maintanences', () => {
    cy.fixture('registry-status.json').then((statusData) => {
      cy.visit('/organization/testorg', {
        onBeforeLoad(win) {
          // Mock window.StatusPage library API
          // The intercept above prevents the real script from loading, but we need to
          // simulate what that script would define to test the useServiceStatus hook
          (win as any).StatusPage = {
            page: class {
              summary(callbacks: {success: (data: any) => void}) {
                // Async callback to simulate library behavior
                setTimeout(() => {
                  callbacks.success(statusData);
                }, 0);
              }
            },
          };
        },
      });
    });
    cy.wait('@getConfig');
    cy.contains('incident1').should(
      'have.attr',
      'href',
      'https://stspg.io/incident1',
    );
    cy.contains('incident2').should(
      'have.attr',
      'href',
      'https://stspg.io/incident2',
    );
    cy.contains(`Scheduled for ${formatDate('2024-02-09T10:00:00.000-05:00')}`);
    cy.contains('maintenance1').should(
      'have.attr',
      'href',
      'https://stspg.io/maintenance1',
    );
    cy.contains('In progress:');
    cy.contains('maintenance2').should(
      'have.attr',
      'href',
      'https://stspg.io/maintenance2',
    );
  });

  it('Displays no incidents and maintanences', () => {
    cy.fixture('registry-status.json').then((statusFixture) => {
      statusFixture.incidents = [];
      statusFixture.scheduled_maintenances = [];
      cy.visit('/organization/testorg', {
        onBeforeLoad(win) {
          // Mock window.StatusPage library API
          // The intercept above prevents the real script from loading, but we need to
          // simulate what that script would define to test the useServiceStatus hook
          (win as any).StatusPage = {
            page: class {
              summary(callbacks: {success: (data: any) => void}) {
                // Async callback to simulate library behavior
                setTimeout(() => {
                  callbacks.success(statusFixture);
                }, 0);
              }
            },
          };
        },
      });
    });
    cy.wait('@getConfig');
    cy.get('#registry-status').should('not.exist');
  });
});
