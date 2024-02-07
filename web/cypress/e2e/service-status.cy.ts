/// <reference types="cypress" />
import {formatDate} from '../../src/libs/utils';

describe('Default permissions page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Displays incidents and maintanences', () => {
    cy.intercept(
      'GET',
      'https://dn6mqn7xvzz3.statuspage.io/api/v2/summary.json',
      {fixture: 'registry-status.json'},
    );
    cy.visit('/organization/testorg');
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
      cy.intercept(
        'GET',
        'https://dn6mqn7xvzz3.statuspage.io/api/v2/summary.json',
        statusFixture,
      );
    });
    cy.visit('/organization/testorg');
    cy.get('#registry-status').should('not.exist');
  });
});
