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
    cy.get('[data-testid="auto-prune-method"]').select('By number of tags');
    cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    cy.get('input[aria-label="number of tags"]').type('{end}{backspace}5');
    cy.contains('Save').click();
  };

  const attemptCreateCreationDateRepoPolicy = (cy) => {
    cy.get('[data-testid="auto-prune-method"]').select('By age of tags');
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

  const createMultiplePolicies = (cy) => {
    // Create initial policy
    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    cy.contains('Add Policy').trigger('click');
    cy.get('#autoprune-policy-form-1', {timeout: 3000}).should('be.visible');

    // Create second policy
    cy.get('#autoprune-policy-form-1').within(() => {
      attemptCreateCreationDateRepoPolicy(cy);
    });

    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '2',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('weeks');
  };

  it('creates repo policy based on number of tags', () => {
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create policy
    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');
  });

  it('creates repo policy based on creation date', () => {
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

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
    cy.get('[data-testid="auto-prune-method"]').contains('None');

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
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create initial policy
    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    // Delete policy
    cy.get('[data-testid="auto-prune-method"]').select('None');
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
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    attemptCreateTagNumberRepoPolicy(cy);
    attemptCreateCreationDateRepoPolicy(cy);
    cy.contains('Could not update repository auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to delete repo policy', () => {
    cy.intercept('DELETE', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/repository/projectquay/repo1?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    attemptCreateTagNumberRepoPolicy(cy);
    cy.contains('Successfully created repository auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    cy.get('[data-testid="auto-prune-method"]').select('None');
    cy.contains('Save').click();
    cy.contains('Could not delete repository auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('shows corresponding namespace policy under repository auto-prune policies section', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create namespace policy
    cy.get('[data-testid="auto-prune-method"]').select('By number of tags');
    cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    cy.get('input[aria-label="tag pattern"]').type('v1.*');
    cy.get('select[aria-label="tag pattern matches"]').select('does not match');
    // Since we're using an older version of numberinput, the field can never be empty and will
    // always include a 0. Here we backspace to remove that 0.
    cy.get('input[aria-label="number of tags"]').type('{end}{backspace}5');
    cy.contains('Save').click();

    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    // Navigate to repository auto-prune policy under repository settings
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Verify that namespace policy is shown
    cy.get('[data-testid="namespace-auto-prune-policy-heading"]').contains(
      'Namespace Auto-Pruning Policies',
    );
    cy.get('[data-testid="namespace-autoprune-policy-method"]').contains(
      'Number of Tags',
    );
    cy.get('[data-testid="namespace-autoprune-policy-value"]').contains('25');
    cy.get('[data-testid="namespace-autoprune-policy-tag-pattern"]').contains(
      'v1.*',
    );
    cy.get(
      '[data-testid="namespace-autoprune-policy-tag-pattern-matches"]',
    ).contains('does not match');
  });

  it('shows the registry autoprune policy', () => {
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="registry-autoprune-policy-method"]').contains(
      'Number of Tags',
    );
    cy.get('[data-testid="registry-autoprune-policy-value"]').contains('10');
  });

  it('creates policy with tag filter', () => {
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').select('By age of tags');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '7',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('days');
    cy.get('input[aria-label="tag creation date value"]').type(
      '2{leftArrow}{backspace}',
    );
    cy.get('select[aria-label="tag creation date unit"]').select('weeks');
    cy.get('input[aria-label="tag pattern"]').type('v1.*');
    cy.get('select[aria-label="tag pattern matches"]').select('does not match');
    cy.contains('Save').click();
  });

  it('create multiple policies', () => {
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    createMultiplePolicies(cy);
  });

  it('update with multiple policies', () => {
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Auto-Prune Policies').click();

    createMultiplePolicies(cy);

    // Update second policy
    cy.get('#autoprune-policy-form-1').within(() => {
      cy.get('[data-testid="auto-prune-method"]').select('By number of tags');
      cy.contains('Save').click();
    });
    cy.contains('Successfully updated repository auto-prune policy');
    cy.get('#autoprune-policy-form-1').within(() => {
      cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    });
  });

  it('delete with multiple policies', () => {
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Auto-Prune Policies').click();

    // Create initial policy
    createMultiplePolicies(cy);

    // Delete second policy
    cy.get('#autoprune-policy-form-1').within(() => {
      cy.get('[data-testid="auto-prune-method"]').select('None');
      cy.contains('Save').click();
    });

    cy.contains('Successfully deleted repository auto-prune policy');

    // second policy form should not exist
    cy.get('#autoprune-policy-form-1').should('not.exist');

    // Delete first policy
    cy.get('#autoprune-policy-form-0').within(() => {
      cy.get('[data-testid="auto-prune-method"]').select('None');
      cy.contains('Save').click();
    });

    cy.contains('Successfully deleted repository auto-prune policy');
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // second policy form should not exist
    cy.get('#autoprune-policy-form-1').should('not.exist');
  });

  it('user policies under user repository autoprune policies tab', () => {
    cy.visit('/organization/user1?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create namespace policy
    cy.get('[data-testid="auto-prune-method"]').select('By number of tags');
    cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    cy.get('input[aria-label="tag pattern"]').type('v1.*');
    cy.get('select[aria-label="tag pattern matches"]').select('does not match');
    cy.get('input[aria-label="number of tags"]').type('{end}{backspace}5');
    cy.contains('Save').click();

    // switch to hello-world repository under user namespace
    cy.visit('/repository/user1/hello-world?tab=settings');
    cy.contains('Repository Auto-Prune Policies').click();

    cy.get('[data-testid="namespace-auto-prune-policy-heading"]').contains(
      'Namespace Auto-Pruning Policies',
    );
    cy.get('[data-testid="namespace-autoprune-policy-method"]').contains(
      'Number of Tags',
    );
    cy.get('[data-testid="namespace-autoprune-policy-value"]').contains('25');
    cy.get('[data-testid="namespace-autoprune-policy-tag-pattern"]').contains(
      'v1.*',
    );
    cy.get(
      '[data-testid="namespace-autoprune-policy-tag-pattern-matches"]',
    ).contains('does not match');
  });
});
