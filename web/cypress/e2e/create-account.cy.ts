/// <reference types="cypress" />

describe('Create Account Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    // Common intercepts for create account tests
    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-token'},
    }).as('getCsrfToken');

    cy.visit('/createaccount');
  });

  // Helper function to setup successful account creation + auto-login
  const setupSuccessfulFlow = () => {
    cy.intercept('POST', '/api/v1/user/', {statusCode: 200}).as('createUser');
    cy.intercept('POST', '/api/v1/signin', {
      statusCode: 200,
      body: {success: true},
    }).as('signinUser');
  };

  // Helper function to setup failed account creation
  const setupFailedCreation = (statusCode = 409, body = {}) => {
    cy.intercept('POST', '/api/v1/user/', {
      statusCode,
      body,
    }).as('createUserFail');
  };

  // Helper function to setup successful creation but failed auto-login
  const setupCreationWithLoginFailure = () => {
    cy.intercept('POST', '/api/v1/user/', {statusCode: 200}).as('createUser');
    cy.intercept('POST', '/api/v1/signin', {
      statusCode: 403,
      body: {error: 'CSRF token was invalid'},
    }).as('signinUserFail');
  };

  it('Form validation works correctly', () => {
    cy.visit('/createaccount');

    // Test empty form submission
    cy.get('button[type=submit]').should('be.disabled');

    // Test invalid username
    cy.get('#username').type('ab'); // Too short
    cy.contains('Username must be at least 3 characters');

    cy.get('#username').clear().type('invalid@username'); // Invalid characters
    cy.contains('Username must be at least 3 characters');

    // Test invalid email
    cy.get('#email').type('invalid-email');
    cy.contains('Please enter a valid email address');

    // Test invalid password
    cy.get('#password').type('123'); // Too short
    cy.contains('Password must be at least 8 characters long');

    // Test password mismatch
    cy.get('#password').clear().type('validpassword123');
    cy.get('#confirm-password').type('differentpassword');
    cy.contains('Passwords must match');

    // Form should still be disabled
    cy.get('button[type=submit]').should('be.disabled');
  });

  it('Successful account creation with valid inputs', () => {
    const testUser = {
      username: `testuser${Date.now()}`,
      email: `test${Date.now()}@example.com`,
      password: 'validpassword123',
    };

    setupSuccessfulFlow();

    // Fill form with valid data
    cy.get('#username').type(testUser.username);
    cy.get('#email').type(testUser.email);
    cy.get('#password').type(testUser.password);
    cy.get('#confirm-password').type(testUser.password);

    // Form should be enabled
    cy.get('button[type=submit]').should('not.be.disabled');

    // Submit form
    cy.get('button[type=submit]').click();

    // Verify API calls were made
    cy.wait('@createUser').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        username: testUser.username,
        email: testUser.email,
        password: testUser.password,
      });
    });

    cy.wait('@getCsrfToken');
    cy.wait('@signinUser').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        username: testUser.username,
        password: testUser.password,
      });
    });

    // Should redirect to organization page after auto-login
    cy.url().should('include', '/organization');
  });

  it('Handles account creation with existing username', () => {
    setupFailedCreation(409, {error_message: 'The username already exists'});

    // Fill form with existing user data
    cy.get('#username').type('user1'); // Existing user from seed data
    cy.get('#email').type('test@example.com');
    cy.get('#password').type('validpassword123');
    cy.get('#confirm-password').type('validpassword123');

    // Submit form
    cy.get('button[type=submit]').click();

    // Should show error message
    cy.wait('@createUserFail');
    cy.contains('Username or email already exists');

    // Should not redirect
    cy.url().should('include', '/createaccount');
  });

  it('Handles account creation success but auto-login failure', () => {
    const testUser = {
      username: `testuser${Date.now()}`,
      email: `test${Date.now()}@example.com`,
      password: 'validpassword123',
    };

    setupCreationWithLoginFailure();

    // Fill form
    cy.get('#username').type(testUser.username);
    cy.get('#email').type(testUser.email);
    cy.get('#password').type(testUser.password);
    cy.get('#confirm-password').type(testUser.password);

    // Submit form
    cy.get('button[type=submit]').click();

    // Wait for calls
    cy.wait('@createUser');
    cy.wait('@getCsrfToken');
    cy.wait('@signinUserFail');

    // Should redirect to signin page with message
    cy.url().should('include', '/signin');
    cy.url().should('include', 'account_created=true');
    cy.url().should('include', 'auto_login_failed=true');
  });

  it('Navigation to signin page works', () => {
    cy.visit('/createaccount');

    // Click "Sign in" link
    cy.contains('Already have an account?').parent().find('a').click();

    // Should navigate to signin page
    cy.url().should('include', '/signin');
  });

  it('Displays proper form labels and structure', () => {
    cy.visit('/createaccount');

    // Check page title
    cy.contains('Create Account');

    // Check form fields exist with proper labels
    cy.contains('Username');
    cy.get('#username').should('exist');

    cy.contains('Email');
    cy.get('#email').should('exist');

    cy.contains('Password');
    cy.get('#password').should('exist');

    cy.contains('Confirm Password');
    cy.get('#confirm-password').should('exist');

    // Check submit button
    cy.get('button[type=submit]').contains('Create Account');

    // Check signin link
    cy.contains('Already have an account?');
    cy.contains('Sign in');
  });

  it('Shows email verification message when awaiting_verification is true', () => {
    const testUser = {
      username: `testuser${Date.now()}`,
      email: `test${Date.now()}@example.com`,
      password: 'validpassword123',
    };

    // Setup account creation with awaiting_verification response
    cy.intercept('POST', '/api/v1/user/', {
      statusCode: 200,
      body: {awaiting_verification: true},
    }).as('createUserAwaitingVerification');

    // Setup signin intercept to verify it's NOT called
    cy.intercept('POST', '/api/v1/signin', (req) => {
      throw new Error('Signin should not be called when awaiting verification');
    }).as('signinShouldNotBeCalled');

    cy.visit('/createaccount');

    // Fill form with valid data
    cy.get('#username').type(testUser.username);
    cy.get('#email').type(testUser.email);
    cy.get('#password').type(testUser.password);
    cy.get('#confirm-password').type(testUser.password);

    // Submit form
    cy.get('button[type=submit]').click();

    // Wait for create user API call
    cy.wait('@createUserAwaitingVerification').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        username: testUser.username,
        email: testUser.email,
        password: testUser.password,
      });
    });

    // Should show verification message
    cy.get('[data-testid="awaiting-verification-alert"]').should('be.visible');
    cy.contains(
      'Thank you for registering! We have sent you an activation email.',
    );
    cy.contains('verify your email address').should('be.visible');

    // Form should be hidden (check visibility, not existence since display:none keeps elements in DOM)
    cy.get('#username').should('not.be.visible');
    cy.get('#email').should('not.be.visible');
    cy.get('#password').should('not.be.visible');

    // Should not redirect to organization page
    cy.url().should('include', '/createaccount');
    cy.url().should('not.include', '/organization');

    // Should show sign in link (it's outside the form when awaiting verification)
    // Find the visible link that's not inside a hidden form
    cy.get('a[href="/signin"]').should('be.visible');
    // The text should also be visible (rendered outside the hidden form)
    cy.contains('body', 'Already have an account?').should('be.visible');

    // Verify no auto-login was attempted - signin API should not be called
    // If signin was attempted, it would have thrown an error from the intercept
    cy.wait(500); // Small wait to ensure no signin API call is made
  });
});
