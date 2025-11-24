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

  it('successfully confirms username', () => {
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

  it('redirects to home page instead of signin after OAuth username confirmation', () => {
    // Simulate OAuth flow: localStorage contains signin page as redirect URL
    cy.window().then((win) => {
      win.localStorage.setItem(
        'quay.redirectAfterLoad',
        'http://localhost:9000/signin',
      );
    });

    let updateCalled = false;

    // Intercept user fetches - return different responses before and after update
    cy.intercept('GET', '/api/v1/user/', (req) => {
      if (updateCalled) {
        // After update: user has no prompts
        req.reply({
          statusCode: 200,
          body: {
            username: 'oauth_user_123',
            anonymous: false,
            prompts: [],
          },
        });
      } else {
        // Before update: user has confirm_username prompt
        req.reply({
          statusCode: 200,
          body: {
            username: 'oauth_user_123',
            anonymous: false,
            prompts: ['confirm_username'],
          },
        });
      }
    }).as('getUser');

    // Mock API calls that home page makes (to prevent 401 redirects)
    cy.intercept('GET', '/api/v1/user/notifications', {
      statusCode: 200,
      body: {notifications: []},
    }).as('getNotifications');

    cy.intercept('GET', '/api/v1/user/robots*', {
      statusCode: 200,
      body: {robots: []},
    }).as('getRobots');

    cy.intercept('GET', '/api/v1/repository*', {
      statusCode: 200,
      body: {repositories: []},
    }).as('getRepositories');

    cy.intercept('GET', '/api/v1/users/*', {
      statusCode: 404,
      body: {username: 'oauth_user_123'},
    }).as('validateUsername');
    cy.intercept('GET', '/api/v1/organization/oauth_user_123', {
      statusCode: 404,
    }).as('validateOrg');

    cy.intercept('PUT', '/api/v1/user/', (req) => {
      updateCalled = true;
      req.reply({
        statusCode: 200,
        body: {
          username: 'oauth_user_123',
          anonymous: false,
          prompts: [],
        },
      });
    }).as('updateUser');

    cy.visit('/updateuser');
    cy.wait('@getUser');

    cy.get('button[type="submit"]').click();
    cy.wait('@updateUser');

    // Should NOT redirect back to signin (the bug we're fixing)
    cy.url().should('not.include', '/signin');
    // Should NOT be on updateuser page anymore
    cy.url().should('not.include', '/updateuser');
    // Should be on an authenticated page (home or organization page)
    cy.url().should('match', /\/(organization)?$/);

    // Verify localStorage was cleaned up
    cy.window().then((win) => {
      expect(win.localStorage.getItem('quay.redirectAfterLoad')).to.be.null;
    });
  });
});
