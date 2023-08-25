/// <reference types="cypress" />

describe('Config tool', () => {
  it('should provide core functionality', () => {
    cy.intercept('/api/v1/config').as('config');
    cy.intercept('/api/v1/config/validate?mode=online').as('validate');
    cy.intercept('/api/v1/config/download').as('download');

    cy.visit('http://quayconfig:qwerty@localhost:8080'); // notsecret
    cy.wait('@config');
    cy.get('h2').should('contain', 'Red Hat Quay Setup');

    cy.get('label').contains('Enable Action Log Rotation').parent('label').find('input').should('not.be.checked');
    cy.get('td').contains('Log Rotation Threshold').should('not.exist');
    cy.get('.cor-floating-bottom-bar').should('contain', 'Validate Configuration Changes');

    cy.get('label').contains('Enable Action Log Rotation').click();
    cy.get('td').contains('Log Rotation Threshold').should('be.visible');
    cy.get('.cor-floating-bottom-bar').should('contain', '2 configuration fields remaining');

    cy.get('label').contains('Enable Action Log Rotation').click();
    cy.get('td').contains('Log Rotation Threshold').should('not.exist');
    cy.get('.cor-floating-bottom-bar').should('contain', 'Validate Configuration Changes');

    cy.get('.cor-floating-bottom-bar button').contains('Validate Configuration Changes').click();
    cy.wait('@validate');
    cy.get('.modal-footer:not(.ng-hide) button.btn-primary').contains('Download').click();
    cy.wait('@download');
    cy.readFile('cypress/downloads/quay-config.tar.gz').should('exist');
  });
});
