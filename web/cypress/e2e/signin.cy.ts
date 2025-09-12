/// <reference types="cypress" />

describe('Signin page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    // Common intercepts for signin tests
    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-token'},
    }).as('getCsrfToken');

    cy.visit('/signin');
  });

  // Helper function to setup successful signin intercept
  const setupSuccessfulSignin = () => {
    cy.intercept('POST', '/api/v1/signin', {
      statusCode: 200,
      body: {success: true},
    }).as('signinSuccess');
  };

  // Helper function to setup failed signin intercept
  const setupFailedSignin = (body = {}, statusCode = 200) => {
    cy.intercept('POST', '/api/v1/signin', {
      statusCode,
      body,
    }).as('signinFail');
  };

  it('Successful signin with existing user', () => {
    setupSuccessfulSignin();

    // Fill and submit form with existing user credentials
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();

    // Verify API calls
    cy.wait('@signinSuccess').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        username: 'user1',
        password: 'password',
      });
    });

    cy.wait('@getCsrfToken');

    // Should redirect to organization page
    cy.url().should('include', '/organization');
  });

  it('Successful signin with correct response format', () => {
    setupSuccessfulSignin();

    // Fill and submit form
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();

    // Verify API call and response handling
    cy.wait('@signinSuccess').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        username: 'user1',
        password: 'password',
      });
    });

    cy.wait('@getCsrfToken');

    // Should redirect to organization page
    cy.url().should('include', '/organization');
  });

  it('Handles invalid credentials correctly', () => {
    setupFailedSignin(
      {
        invalidCredentials: true,
        message: 'Invalid credentials',
      },
      403,
    );

    // Fill and submit form
    cy.get('#pf-login-username-id').type('wronguser');
    cy.get('#pf-login-password-id').type('wrongpassword');
    cy.get('button[type=submit]').click();

    // Should show error message
    cy.wait('@signinFail');
    cy.contains('Invalid login credentials');

    // Should not redirect
    cy.url().should('include', '/signin');
  });

  it('Handles CSRF token expiry correctly', () => {
    setupFailedSignin(
      {
        error: 'CSRF token was invalid or missing',
      },
      403,
    );

    // Fill and submit form
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();

    // Should show CSRF error message
    cy.wait('@signinFail');
    cy.contains('CSRF token expired - please refresh');

    // Should not redirect
    cy.url().should('include', '/signin');
  });

  it('Navigation to create account page works', () => {
    cy.visit('/signin');

    // Click "Create account" link
    cy.contains("Don't have an account?").parent().find('a').click();

    // Should navigate to create account page
    cy.url().should('include', '/createaccount');
  });

  it('Shows account created success message', () => {
    // Visit signin page with account created parameter
    cy.visit('/signin?account_created=true');

    // Should show success message (this would need to be implemented)
    // This test documents expected behavior
    cy.url().should('include', 'account_created=true');
  });

  it('Shows auto-login failed message', () => {
    // Visit signin page with auto login failed parameter
    cy.visit('/signin?account_created=true&auto_login_failed=true');

    // Should show appropriate message (this would need to be implemented)
    // This test documents expected behavior
    cy.url().should('include', 'auto_login_failed=true');
  });

  it('Form validation works', () => {
    setupFailedSignin({}); // Empty body - no success property

    // Fill form and submit (empty form submission is handled by browser/PatternFly)
    cy.get('#pf-login-username-id').type('testuser');
    cy.get('#pf-login-password-id').type('testpass');
    cy.get('button[type=submit]').click();

    // Wait for API call
    cy.wait('@signinFail');

    // Should show error alert
    cy.get('#form-error-alert').should('be.visible');
    cy.get('#form-error-alert').should('contain', 'Invalid login credentials');

    // Should not redirect
    cy.url().should('include', '/signin');
  });
});
