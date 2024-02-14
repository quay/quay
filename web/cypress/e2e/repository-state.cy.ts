/// <reference types="cypress" />

describe('Repository Settings - Repo State', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['REPO_MIRROR'] = true;
        return res;
      }),
    ).as('getConfig');
  });

  it('Should not be visible without FEATURE_REPO_MIRROR', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['REPO_MIRROR'] = false;
        return res;
      }),
    ).as('getConfigNoRepoMirror');
    cy.visit('/repository/user1/nested/repo?tab=settings');
    cy.contains('Repository state').should('not.exist');
  });

  it.skip('Can switch between states', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['REPO_MIRROR'] = true;
        return res;
      }),
    ).as('getConfig');
    cy.visit('/repository/user1/nested/repo?tab=settings');
    cy.contains('Repository state').should('exist');
  });
});
