/// <reference types="cypress" />

describe('Namespace settings - autoprune policies', () => {
    beforeEach(() => {
      cy.exec('npm run quay:seed');
      cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
        .then((response) => response.body.csrf_token)
        .then((token) => {
          cy.loginByCSRF(token);
        });
    });

    const attemptCreateTagNumberPolicy = (cy) => {
        cy.get('[data-testid="namespace-auto-prune-method"]').select('By number of tags');
        cy.get('input[aria-label="number of tags"]').should('have.value', '10');
        cy.get('input[aria-label="number of tags"]').type('{end}{backspace}5');
        cy.contains('Save').click();
    }

    const attemptCreateCreationDatePolicy = (cy) => {
        cy.get('[data-testid="namespace-auto-prune-method"]').select('By age of tags');
        cy.get('input[aria-label="age of tags"]').should('have.value', '7d');
        cy.get('input[aria-label="age of tags"]').clear();
        cy.get('input[aria-label="age of tags"]').type('2w');
        cy.contains('Save').click();
    }

    it('creates policy based on number of tags', () => {
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.get('[data-testid="namespace-auto-prune-method"]').contains('None');

        // Create policy
        attemptCreateTagNumberPolicy(cy);
        cy.contains('Successfully created auto-prune policy');
        cy.get('input[aria-label="number of tags"]').should('have.value', '15');
    });
    
    it('creates policy based on creation date', () => {
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.get('[data-testid="namespace-auto-prune-method"]').contains('None');

        // Create policy
        attemptCreateCreationDatePolicy(cy);
        cy.contains('Successfully created auto-prune policy');
        cy.get('input[aria-label="age of tags"]').should('have.value', '2w');
    });
    
    it('updates policy', () => {
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.get('[data-testid="namespace-auto-prune-method"]').contains('None');

        // Create initial policy
        attemptCreateTagNumberPolicy(cy);
        cy.contains('Successfully created auto-prune policy');
        cy.get('input[aria-label="number of tags"]').should('have.value', '15');

        // Update policy
        attemptCreateCreationDatePolicy(cy);
        cy.contains('Successfully updated auto-prune policy');
        cy.get('input[aria-label="age of tags"]').should('have.value', '2w');
    });
    
    it('deletes policy', () => {
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.get('[data-testid="namespace-auto-prune-method"]').contains('None');

        // Create initial policy
        attemptCreateTagNumberPolicy(cy);
        cy.contains('Successfully created auto-prune policy');
        cy.get('input[aria-label="number of tags"]').should('have.value', '15');

        // Delete policy
        cy.get('[data-testid="namespace-auto-prune-method"]').select('None');
        cy.contains('Save').click();
        cy.contains('Successfully deleted auto-prune policy');
    });

    it('displays error when failing to load policy', () => {
        cy.intercept('GET', '**/autoprunepolicy/**', {statusCode: 500}).as('getServerFailure');
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.contains('Unable to complete request');
        cy.contains('AxiosError: Request failed with status code 500');
    });

    it('displays error when failing to create policy', () => {
        cy.intercept('POST', '**/autoprunepolicy/**', {statusCode: 500}).as('getServerFailure');
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();

        attemptCreateTagNumberPolicy(cy);
        cy.contains('Could not create auto-prune policy');
        cy.get('button[aria-label="Danger alert details"]').click();
        cy.contains('AxiosError: Request failed with status code 500');
    });

    it('displays error when failing to update policy', () => {
        cy.intercept('PUT', '**/autoprunepolicy/**', {statusCode: 500}).as('getServerFailure');
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.get('[data-testid="namespace-auto-prune-method"]').contains('None');

        attemptCreateTagNumberPolicy(cy);
        attemptCreateCreationDatePolicy(cy);
        cy.contains('Could not update auto-prune policy');
        cy.get('button[aria-label="Danger alert details"]').click();
        cy.contains('AxiosError: Request failed with status code 500');
    });

    it('displays error when failing to delete policy', () => {
        cy.intercept('DELETE', '**/autoprunepolicy/**', {statusCode: 500}).as('getServerFailure');
        cy.visit('/organization/testorg?tab=Settings');
        cy.contains('Auto-Prune Policies').click();
        cy.get('[data-testid="namespace-auto-prune-method"]').contains('None');

        attemptCreateTagNumberPolicy(cy);
        cy.contains('Successfully created auto-prune policy');
        cy.get('input[aria-label="number of tags"]').should('have.value', '15');

        cy.get('[data-testid="namespace-auto-prune-method"]').select('None');
        cy.contains('Save').click();
        cy.contains('Could not delete auto-prune policy');
        cy.get('button[aria-label="Danger alert details"]').click();
        cy.contains('AxiosError: Request failed with status code 500');
    });
    
    // TODO: Uncomment once user settings is supported
    // it('updates policy for users', () => {
    //     cy.visit('/organization/user1?tab=Settings');
    //     cy.contains('Auto-Prune Policies').click();

    //     // Create initial policy
    //     attemptCreateTagNumberPolicy(cy);
    //     cy.contains('Successfully created auto-prune policy');
    //     cy.get('input[aria-label="number of tags"]').should('have.value', '15');

    //     // Update policy
    //     attemptCreateCreationDatePolicy(cy);
    //     cy.contains('Successfully updated auto-prune policy');
    //     cy.get('input[aria-label="age of tags"]').should('have.value', '2w');
    // });
});
