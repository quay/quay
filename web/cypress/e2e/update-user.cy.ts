/// <reference types="cypress" />

// Handle QuaySidebar config errors in tests
Cypress.on('uncaught:exception', (err, runnable) => {
  // Ignore QuaySidebar config errors in tests
  if (err.message.includes('quay_io')) {
    return false;
  }
  return true;
});

describe('Update User Component', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-csrf-token'},
    }).as('getCsrfToken');

    cy.intercept('GET', '/config', {
      body: {
        features: {
          DIRECT_LOGIN: true,
          USERNAME_CONFIRMATION: true,
          MAILING: true,
          USER_CREATION: true,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
          SERVER_HOSTNAME: 'localhost:8080',
        },
        external_login: [],
        registry_state: 'normal',
      },
    }).as('getConfig');
  });

  it('redirects non-authenticated users to signin', () => {
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {message: 'Unauthorized'},
    }).as('getUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.url().should('include', '/signin');
  });

  it('displays username confirmation form', () => {
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'auto_generated_user123',
        anonymous: false,
        prompts: ['confirm_username'],
      },
    }).as('getUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.get('h2').should('contain.text', 'Confirm Username');
    cy.get('#username').should('have.value', 'auto_generated_user123');
    cy.get('button[type="submit"]').should('contain.text', 'Confirm Username');
  });

  it.only('successfully confirms username', () => {
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'auto_generated_user123',
        anonymous: false,
        prompts: ['confirm_username'],
      },
    }).as('getUser');

    cy.intercept('GET', '/api/v1/users/*', {
      statusCode: 404,
      body: {username: 'test_signin_username'},
    }).as('validateUsername');
    cy.intercept('GET', '/api/v1/organization/test_signin_username', {
      statusCode: 404,
    }).as('validateOrg');

    cy.intercept('PUT', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'test_signin_username',
        anonymous: false,
        prompts: [],
      },
    }).as('updateUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.get('#username').clear().type('test_signin_username');
    cy.wait(['@validateUsername', '@validateOrg']);
    cy.get('button[type="submit"]').click();
    cy.wait('@updateUser');

    cy.url().should('not.include', '/updateuser');
  });

  it('displays profile form for metadata prompts', () => {
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'user1',
        anonymous: false,
        prompts: ['enter_name'],
      },
    }).as('getUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.get('h2').should('contain.text', 'Tell us a bit more about yourself');
    cy.get('#given-name').should('be.visible');
    cy.get('button[type="submit"]').should('be.disabled');
    cy.get('button').should('contain.text', 'No thanks');
  });

  it('successfully saves profile metadata', () => {
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'user1',
        anonymous: false,
        prompts: ['enter_name'],
      },
    }).as('getUser');

    cy.intercept('PUT', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'user1',
        anonymous: false,
        prompts: [],
      },
    }).as('updateUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.get('#given-name').type('John');
    cy.get('button[type="submit"]').click();
    cy.wait('@updateUser');

    cy.url().should('not.include', '/updateuser');
  });

  it('allows skipping profile metadata', () => {
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'user1',
        anonymous: false,
        prompts: ['enter_name'],
      },
    }).as('getUser');

    cy.intercept('PUT', '/api/v1/user/', {
      statusCode: 200,
      body: {
        username: 'user1',
        anonymous: false,
        prompts: [],
      },
    }).as('updateUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.get('button').contains('No thanks').click();
    cy.wait('@updateUser');

    cy.url().should('not.include', '/updateuser');
  });
});
