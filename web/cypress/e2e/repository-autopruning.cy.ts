/// <reference types="cypress" />

describe('Repository settings - Repository autoprune policies', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
  });

  const attemptCreateTagNumberRepoPolicy = (cy) => {
    cy.get('[data-testid="repository-auto-prune-method"]').select(
      'By number of tags',
    );
    cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    cy.get('input[aria-label="number of tags"]').type('{end}{backspace}5');
    cy.contains('Save').click();
  };

  const attemptCreateCreationDateRepoPolicy = (cy) => {
    cy.get('[data-testid="repository-auto-prune-method"]').select(
      'By age of tags',
    );
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '7',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('days');
    cy.get('input[aria-label="tag creation date value"]').type(
      '2{leftArrow}{backspace}',
    );
    cy.get('select[aria-label="tag creation date unit"]').select('weeks');
    cy.contains('Save').click();
  };

  it('creates repo policy based on number of tags', () => {
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="repository-auto-prune-method"]').contains('None');

    // Create policy
    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');
  });

  it('creates repo policy based on creation date', () => {
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="repository-auto-prune-method"]').contains('None');

    // Create policy
    attemptCreateCreationDateRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '2',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('weeks');
  });

  it('updates repo policy', () => {
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="repository-auto-prune-method"]').contains('None');

    // Create initial policy
    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    // Update policy
    attemptCreateCreationDateRepoPolicy(cy);
    cy.contains('Successfully updated repository auto-prune policy');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '2',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('weeks');
  });

  it('deletes repo policy', () => {
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="repository-auto-prune-method"]').contains('None');

    // Create initial policy
    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    // Delete policy
    cy.get('[data-testid="repository-auto-prune-method"]').select('None');
    cy.contains('Save').click();
    cy.contains('Successfully deleted repository auto-prune policy');
  });

  it('displays error when failing to load repo policy', () => {
    cy.intercept('GET', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.contains('Unable to complete request');
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to create repo policy', () => {
    cy.intercept('POST', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();

    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Could not create repository auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to update repo policy', () => {
    cy.intercept('PUT', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="repository-auto-prune-method"]').contains('None');

    attemptCreateTagNumberRepoPolicy(cy);
    attemptCreateCreationDateRepoPolicy(cy);
    cy.contains('Could not update auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to delete repo policy', () => {
    cy.intercept('DELETE', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="repository-auto-prune-method"]').contains('None');

    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    cy.get('[data-testid="repository-auto-prune-method"]').select('None');
    cy.contains('Save').click();
    cy.contains('Could not delete auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

});
