/// <reference types="cypress" />

import {humanizeTimeForExpiry, parseTimeDuration} from 'src/libs/utils';

describe('Account Settings Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.visit('/signin');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
  });

  it('General Settings', () => {
    cy.visit('/organization/user1?tab=Settings');

    // Type a bad e-mail
    cy.get('#org-settings-email').clear();
    cy.get('#org-settings-email').type('this is not a good e-mail');
    cy.contains('Please enter a valid email address');

    // Leave empty
    cy.get('#org-settings-email').clear();
    cy.contains('Please enter email associate with namespace');

    // check is disabled
    cy.get('#save-org-settings').should('be.disabled');
    cy.get('#org-settings-email').clear();

    // Type a good content
    cy.get('#org-settings-email').type('good-email@redhat.com');
    cy.get('#org-settings-fullname').type('Joe Smith');
    cy.get('#org-settings-location').type('Raleigh, NC');
    cy.get('#org-settings-company').type('Red Hat');
    cy.get('#save-org-settings').click();

    // refresh page and check if email is saved
    cy.reload();
    cy.get('#org-settings-email').should('have.value', 'good-email@redhat.com');
    cy.get('#org-settings-fullname').should('have.value', 'Joe Smith');
    cy.get('#org-settings-location').should('have.value', 'Raleigh, NC');
    cy.get('#org-settings-company').should('have.value', 'Red Hat');
  });

  it('Tag Expiration picker visibility', () => {
    cy.fixture('config.json').then((config) => {
      config.features.CHANGE_TAG_EXPIRATION = false;
      cy.intercept('GET', '/config', config).as('getConfigDisabled');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigDisabled');

    // Verify the FormGroup is not visible
    cy.get('[data-testid="tag-expiration-picker"]').should('not.exist');

    cy.fixture('config.json').then((config) => {
      config.features.CHANGE_TAG_EXPIRATION = true;
      cy.intercept('GET', '/config', config).as('getConfigEnabled');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigEnabled');

    // Verify the FormGroup is visible
    cy.get('[data-testid="tag-expiration-picker"]').should('be.visible');
  });

  it('Tag expiration picker dropdown values', () => {
    cy.fixture('config.json').then((config) => {
      config.features.CHANGE_TAG_EXPIRATION = true;
      cy.intercept('GET', '/config', config).as('getConfigEnabled');
    });
    cy.intercept('GET', '/api/v1/user', (req) => {
      req.continue((res) => {
        res.body.tag_expiration_s = 60 * 60 * 24 * 80; // 80 days in seconds
      });
    }).as('getUser');

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigEnabled');
    cy.wait('@getUser');

    // Verify the dropdown values
    cy.fixture('config.json').then((config) => {
      const options = config.config.TAG_EXPIRATION_OPTIONS;
      options.forEach((option, index) => {
        const duration = parseTimeDuration(option);
        const durationInSeconds = duration.asSeconds();
        const humanized = humanizeTimeForExpiry(durationInSeconds);

        cy.get(`[data-testid="tag-expiration-picker"] option:eq(${index})`)
          .should('have.value', durationInSeconds.toString())
          .and('contain', humanized);
      });
    });

    // Verify the correct value is selected
    cy.get('[data-testid="tag-expiration-picker"]').should(
      'have.value',
      60 * 60 * 24 * 80, // Assuming '80d' is the format in the config.json
    );
  });

  it('Billing Information', () => {
    cy.visit('/organization/user1?tab=Settings');

    // navigate to billing tab
    cy.get('#pf-tab-1-billinginformation').click();

    // Type a bad e-mail
    cy.get('#billing-settings-invoice-email').clear();
    cy.get('#billing-settings-invoice-email').type('this is not a good e-mail');

    // check is disabled
    cy.get('#save-billing-settings').should('be.disabled');
    cy.get('#billing-settings-invoice-email').clear();

    // Type a good e-mail and save
    cy.get('#billing-settings-invoice-email').type('invoice-email@redhat.com');

    // check save receipts
    cy.get('#checkbox').should('not.be.checked');
    cy.get('#checkbox').click();

    // Save
    cy.get('#save-billing-settings').click();

    // refresh page, navigate to billing tab and check if email is saved
    cy.reload();
    cy.get('#pf-tab-1-billinginformation').click();
    cy.get('#billing-settings-invoice-email').should(
      'have.value',
      'invoice-email@redhat.com',
    );
    cy.get('#checkbox').should('be.checked');
  });

  it('CLI Token', () => {
    cy.visit('/organization/user1?tab=Settings');

    // navigate to CLI Tab
    cy.get('#pf-tab-2-cliconfig').click();

    // Click generate password
    cy.get('#cli-password-button').click();

    // Wrong password
    cy.get('#delete-confirmation-input').type('wrongpassword');
    cy.get('#submit').click();
    cy.contains('Invalid Username or Password');

    // Correct password
    cy.get('#delete-confirmation-input').clear();
    cy.get('#delete-confirmation-input').type('password');
    cy.get('#submit').click();
    cy.contains('Your encrypted password is');
  });
});
