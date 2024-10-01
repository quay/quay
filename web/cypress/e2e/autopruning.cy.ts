/// <reference types="cypress" />

describe('Namespace settings - autoprune policies', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
  });

  const attemptCreateTagNumberPolicy = (cy) => {
    cy.get('[data-testid="auto-prune-method"]').select('By number of tags');
    cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    // Since we're using an older version of numberinput, the field can never be empty and will
    // always include a 0. Here we backspace to remove that 0.
    cy.get('input[aria-label="number of tags"]').type('{end}{backspace}5');
    cy.contains('Save').click();
  };

  const attemptCreateCreationDatePolicy = (cy) => {
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
    attemptCreateTagNumberPolicy(cy);
    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    cy.contains('Add Policy').click();
    cy.get('#autoprune-policy-form-1', {timeout: 3000}).should('be.visible');

    // Create second policy
    cy.get('#autoprune-policy-form-1').within(() => {
      attemptCreateCreationDatePolicy(cy);
    });

    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '2',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('weeks');
  };

  it('creates policy based on number of tags', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create policy
    attemptCreateTagNumberPolicy(cy);
    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');
  });

  it('creates policy based on creation date', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create policy
    attemptCreateCreationDatePolicy(cy);
    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '2',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('weeks');
  });

  it('updates policy', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create initial policy
    attemptCreateTagNumberPolicy(cy);
    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    // Update policy
    attemptCreateCreationDatePolicy(cy);
    cy.contains('Successfully updated auto-prune policy');
    cy.get('input[aria-label="tag creation date value"]').should(
      'have.value',
      '2',
    );
    cy.get('select[aria-label="tag creation date unit"]').contains('weeks');
  });

  it('deletes policy', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // Create initial policy
    attemptCreateTagNumberPolicy(cy);
    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    // Delete policy
    cy.get('[data-testid="auto-prune-method"]').select('None');
    cy.contains('Save').click();
    cy.contains('Successfully deleted auto-prune policy');
  });

  it('displays error when failing to load policy', () => {
    cy.intercept('GET', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.contains('Unable to complete request');
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to create policy', () => {
    cy.intercept('POST', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();

    attemptCreateTagNumberPolicy(cy);
    cy.contains('Could not create auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to update policy', () => {
    cy.intercept('PUT', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    attemptCreateTagNumberPolicy(cy);
    attemptCreateCreationDatePolicy(cy);
    cy.contains('Could not update auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('displays error when failing to delete policy', () => {
    cy.intercept('DELETE', '**/autoprunepolicy/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    attemptCreateTagNumberPolicy(cy);
    cy.contains('Successfully created auto-prune policy');
    cy.get('input[aria-label="number of tags"]').should('have.value', '25');

    cy.get('[data-testid="auto-prune-method"]').select('None');
    cy.contains('Save').click();
    cy.contains('Could not delete auto-prune policy');
    cy.get('button[aria-label="Danger alert details"]').click();
    cy.contains('AxiosError: Request failed with status code 500');
  });

  it('shows the registry autoprune policy', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="registry-autoprune-policy-method"]').contains(
      'Number of Tags',
    );
    cy.get('[data-testid="registry-autoprune-policy-value"]').contains('10');
  });

  it('creates policy with tag filter', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
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
    cy.contains('Successfully created auto-prune policy');
  });

  // TODO: Uncomment once user settings is supported
  // it('updates policy for users', () => {
  //     cy.visit('/organization/user1?tab=Settings');
  //     cy.contains('Auto-Prune Policies').click();

  //     // Create initial policy
  //     attemptCreateTagNumberPolicy(cy);
  //     cy.contains('Successfully created auto-prune policy');
  //     cy.get('input[aria-label="number of tags"]').should('have.value', '25');

  //     // Update policy
  //     attemptCreateCreationDatePolicy(cy);
  //     cy.contains('Successfully updated auto-prune policy');
  //     cy.get('input[aria-label="tag creation date value"]').should('have.value', '2');
  //     cy.get('div[aria-label="tag creation date unit"]').contains('weeks');
  // });

  it('create multiple policies', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    createMultiplePolicies(cy);
  });

  it('update with multiple policies', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();

    createMultiplePolicies(cy);

    // Update second policy
    cy.get('#autoprune-policy-form-1').within(() => {
      cy.get('[data-testid="auto-prune-method"]').select('By number of tags');
      cy.contains('Save').click();
    });
    cy.contains('Successfully updated auto-prune policy');
    cy.get('#autoprune-policy-form-1').within(() => {
      cy.get('input[aria-label="number of tags"]').should('have.value', '20');
    });
  });

  it('delete with multiple policies', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();

    createMultiplePolicies(cy);

    // Delete second policy
    cy.get('#autoprune-policy-form-1').within(() => {
      cy.get('[data-testid="auto-prune-method"]').select('None');
      cy.contains('Save').click();
    });

    cy.contains('Successfully deleted auto-prune policy');

    // second policy form should not exist
    cy.get('#autoprune-policy-form-1').should('not.exist');

    // Delete first policy
    cy.get('#autoprune-policy-form-0').within(() => {
      cy.get('[data-testid="auto-prune-method"]').select('None');
      cy.contains('Save').click();
    });

    cy.contains('Successfully deleted auto-prune policy');
    cy.get('[data-testid="auto-prune-method"]').contains('None');

    // second policy form should not exist
    cy.get('#autoprune-policy-form-1').should('not.exist');
  });

  it('display multiple namespace auto-pruning policies', () => {
    cy.visit('/organization/testorg?tab=Settings');
    cy.contains('Auto-Prune Policies').click();

    createMultiplePolicies(cy);

    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Auto-Prune Policies').click();

    cy.get('[data-testid="namespace-autoprune-policy-method"]').each(
      ($el, index) => {
        switch (index) {
          case 0:
            cy.wrap($el).should('have.text', 'Number of Tags');
            break;
          case 1:
            cy.wrap($el).should('have.text', 'Age of Tags');
            break;
        }
      },
    );

    cy.get('[data-testid="namespace-autoprune-policy-value"]').each(
      ($el, index) => {
        switch (index) {
          case 0:
            cy.wrap($el).should('have.text', '25');
            break;
          case 1:
            cy.wrap($el).should('have.text', '2w');
            break;
        }
      },
    );
  });
});
