/// <reference types="cypress" />

describe('Repository Settings - Permissions', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.visit('/repository/testorg/testrepo?tab=settings');
  });

  it('Renders permissions', () => {
    const user1Row = cy.get('tr:contains("user1")');
    user1Row.within(() => {
      cy.get(`[data-label="membername"]`).should('have.text', 'user1');
      cy.get(`[data-label="type"]`).should('have.text', ' User ');
      cy.get(`[data-label="role"]`).should('have.text', 'admin');
    });
    const robotRow = cy.get('tr:contains("testorg+testrobot")');
    robotRow.within(() => {
      cy.get(`[data-label="membername"]`).should(
        'have.text',
        'testorg+testrobot',
      );
      cy.get(`[data-label="type"]`).should('have.text', ' Robot ');
      cy.get(`[data-label="role"]`).should('have.text', 'read');
    });
    const teamRow = cy.get('tr:contains("testteam")');
    teamRow.within(() => {
      cy.get(`[data-label="membername"]`).should('have.text', 'testteam');
      cy.get(`[data-label="type"]`).should('have.text', ' Team ');
      cy.get(`[data-label="role"]`).should('have.text', 'read');
    });
  });

  it('Changes user/robot/team permissions inline', () => {
    const user1Row = cy.get('tr:contains("user1")');
    user1Row.within(() => {
      cy.contains('admin').click();
      cy.contains('Read').click();
      cy.get(`[data-label="role"]`).should('have.text', 'read');
    });
    const robotRow = cy.get('tr:contains("testorg+testrobot")');
    robotRow.within(() => {
      cy.contains('read').click();
      cy.contains('Write').click();
      cy.get(`[data-label="role"]`).should('have.text', 'write');
    });
    const teamRow = cy.get('tr:contains("testteam")');
    teamRow.within(() => {
      cy.contains('read').click();
      cy.contains('Write').click();
      cy.get(`[data-label="role"]`).should('have.text', 'write');
    });
  });

  it('Deletes user/robot/team permission inline', () => {
    const user1Row = cy.get('tr:contains("user1")');
    user1Row.within(() => {
      cy.get('[data-label="kebab"]').within(() => cy.get('button').click());
      cy.contains('Delete Permission').click();
      cy.contains('user1').should('not.exist');
    });
    const robotRow = cy.get('tr:contains("testorg+testrobot")');
    robotRow.within(() => {
      cy.get('[data-label="kebab"]').within(() => cy.get('button').click());
      cy.contains('Delete Permission').click();
      cy.contains('testorg+testrobot').should('not.exist');
    });
    const teamRow = cy.get('tr:contains("testteam")');
    teamRow.within(() => {
      cy.get('[data-label="kebab"]').within(() => cy.get('button').click());
      cy.contains('Delete Permission').click();
      cy.contains('testteam').should('not.exist');
    });
  });

  it('Bulk deletes permissions', () => {
    cy.contains('1 - 4 of 4').should('exist');
    cy.get('[name="permissions-select-all"]').click();
    cy.contains('Actions').click();
    cy.get('#bulk-delete-permissions').contains('Delete').click();
    cy.get('table').within(() => {
      cy.contains('user1').should('not.exist');
      cy.contains('testorg+testrobot').should('not.exist');
      cy.contains('testteam').should('not.exist');
    });
  });

  it('Bulk changes permissions', () => {
    cy.contains('1 - 4 of 4').should('exist');
    cy.get('[name="permissions-select-all"]').click();
    cy.contains('Actions').click();
    cy.contains('Change Permissions').click();
    cy.get('[data-testid="change-permissions-menu-list"]').within(() => {
      cy.contains('Write').click();
    });
    const user1Row = cy.get('tr:contains("user1")');
    user1Row.within(() => {
      cy.get(`[data-label="membername"]`).should('have.text', 'user1');
      cy.get(`[data-label="role"]`).should('have.text', 'write');
    });
    const robotRow = cy.get('tr:contains("testorg+testrobot")');
    robotRow.within(() => {
      cy.get(`[data-label="membername"]`).should(
        'have.text',
        'testorg+testrobot',
      );
      cy.get(`[data-label="role"]`).should('have.text', 'write');
    });
    const teamRow = cy.get('tr:contains("testteam")');
    teamRow.within(() => {
      cy.get(`[data-label="membername"]`).should('have.text', 'testteam');
      cy.get(`[data-label="role"]`).should('have.text', 'write');
    });
  });

  it('Adds user/robot/team permission', () => {
    cy.contains('Add permissions').click();
    cy.get('#add-permission-form').within(() => {
      // We need the wait otherwise the dropdown won't open
      cy.wait(2000);
      cy.get('input[placeholder="Search for user, add/create robot account"]')
        .click()
        .type('user');
      cy.get(
        'input[placeholder="Search for user, add/create robot account"]',
      ).should('have.value', 'user');

      cy.get('button:contains("user2")').click();
      cy.contains('admin').click();
      cy.contains('Read').click();
      cy.contains('Submit').click();
    });
    const user2Row = cy.get('tr:contains("user2")');
    user2Row.within(() => {
      cy.get(`[data-label="membername"]`).should('have.text', 'user2');
      cy.get(`[data-label="type"]`).should('have.text', ' User ');
      cy.get(`[data-label="role"]`).should('have.text', 'read');
    });
    cy.contains('Add permissions').click();
    cy.get('#add-permission-form').within(() => {
      // We need the wait otherwise the dropdown won't open
      cy.wait(2000);
      cy.get('input[placeholder="Search for user, add/create robot account"]')
        .click()
        .type('test');
      cy.get(
        'input[placeholder="Search for user, add/create robot account"]',
      ).should('have.value', 'test');

      cy.contains('testorg+testrobot2').click();
      cy.contains('admin').click();
      cy.contains('Read').click();
      cy.contains('Submit').click();
    });
    const testrobot3Row = cy.get('tr:contains("testorg+testrobot2")');
    testrobot3Row.within(() => {
      cy.get(`[data-label="membername"]`).should(
        'have.text',
        'testorg+testrobot2',
      );
      cy.get(`[data-label="type"]`).should('have.text', ' Robot ');
      cy.get(`[data-label="role"]`).should('have.text', 'read');
    });
    cy.contains('Add permissions').click();
    cy.get('#add-permission-form').within(() => {
      // We need the wait otherwise the dropdown won't open
      cy.wait(2000);
      cy.get('input[placeholder="Search for user, add/create robot account"]')
        .click()
        .type('test');
      cy.get(
        'input[placeholder="Search for user, add/create robot account"]',
      ).should('have.value', 'test');

      cy.contains('testteam2').click();
      cy.contains('admin').click();
      cy.contains('Read').click();
      cy.contains('Submit').click();
    });
    const testteam2Row = cy.get('tr:contains("testteam2")');
    testteam2Row.within(() => {
      cy.get(`[data-label="membername"]`).should('have.text', 'testteam2');
      cy.get(`[data-label="type"]`).should('have.text', ' Team ');
      cy.get(`[data-label="role"]`).should('have.text', 'read');
    });
  });
});
