/// <reference types="cypress" />

describe('Signin page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    // Common intercepts for signin tests
    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-token'},
    }).as('getCsrfToken');

    // Mock config endpoint to ensure LoginForm renders
    cy.intercept('GET', '/config', {
      body: {
        features: {
          DIRECT_LOGIN: true,
          USER_CREATION: true,
          MAILING: true,
          INVITE_ONLY_USER_CREATION: false,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfig');

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

  it.skip('Successful signin with existing user', () => {
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

  it.skip('Successful signin with correct response format', () => {
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

describe('Forgot Password functionality', () => {
  beforeEach(() => {
    // Mock config with mailing enabled
    cy.intercept('GET', '/config', {
      body: {
        features: {
          MAILING: true,
          DIRECT_LOGIN: true,
          USER_CREATION: true,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfig');

    cy.visit('/signin');
    cy.wait('@getConfig');
  });

  it('Shows forgot password link when conditions are met', () => {
    cy.contains('Forgot Password?').should('be.visible');
  });

  it('Switches to forgot password view', () => {
    cy.contains('Forgot Password?').click();
    cy.contains('Please enter the e-mail address for your account').should(
      'be.visible',
    );
    cy.contains('Back to Sign In').should('be.visible');
  });

  it('Sends recovery email successfully', () => {
    cy.intercept('POST', '/api/v1/recovery', {
      statusCode: 200,
      body: {status: 'sent'},
    }).as('sendRecovery');

    cy.contains('Forgot Password?').click();
    cy.get('#recovery-email').type('test@example.com');
    cy.contains('Send Recovery Email').click();

    cy.wait('@sendRecovery').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        email: 'test@example.com',
      });
    });

    cy.contains(
      'Instructions on how to reset your password have been sent',
    ).should('be.visible');
  });

  it('Handles recovery email errors', () => {
    cy.intercept('POST', '/api/v1/recovery', {
      statusCode: 400,
      body: {message: 'User not found'},
    }).as('sendRecoveryError');

    cy.contains('Forgot Password?').click();
    cy.get('#recovery-email').type('notfound@example.com');
    cy.contains('Send Recovery Email').click();

    cy.wait('@sendRecoveryError');
    cy.contains('User not found').should('be.visible');
  });

  it('Handles organization account recovery', () => {
    cy.intercept('POST', '/api/v1/recovery', {
      statusCode: 200,
      body: {
        status: 'org',
        orgemail: 'admin@org.com',
        orgname: 'testorg',
      },
    }).as('sendOrgRecovery');

    cy.contains('Forgot Password?').click();
    cy.get('#recovery-email').type('admin@org.com');
    cy.contains('Send Recovery Email').click();

    cy.wait('@sendOrgRecovery');
    cy.contains('admin@org.com').should('be.visible');
    cy.contains('testorg').should('be.visible');
  });

  it('Does not show forgot password when mailing is disabled', () => {
    cy.intercept('GET', '/config', {
      body: {
        features: {
          MAILING: false,
          DIRECT_LOGIN: true,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfigNoMailing');

    cy.visit('/signin');
    cy.wait('@getConfigNoMailing');
    cy.contains('Forgot Password?').should('not.exist');
  });

  it('Does not show forgot password for non-Database auth', () => {
    cy.intercept('GET', '/config', {
      body: {
        features: {
          MAILING: true,
          DIRECT_LOGIN: true,
        },
        config: {
          AUTHENTICATION_TYPE: 'LDAP',
        },
        external_login: [],
      },
    }).as('getConfigLDAP');

    cy.visit('/signin');
    cy.wait('@getConfigLDAP');
    cy.contains('Forgot Password?').should('not.exist');
  });
});

describe('Create Account functionality', () => {
  beforeEach(() => {
    cy.visit('/signin');
  });

  it('Shows create account link when all conditions are met', () => {
    cy.intercept('GET', '/config', {
      body: {
        features: {
          USER_CREATION: true,
          DIRECT_LOGIN: true,
          INVITE_ONLY_USER_CREATION: false,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfigCreateAccount');

    cy.wait('@getConfigCreateAccount');
    cy.contains("Don't have an account?").should('be.visible');
    cy.contains('Create account').should('be.visible');
  });

  it('Shows invitation message when invite-only is enabled', () => {
    cy.intercept('GET', '/config', {
      body: {
        features: {
          USER_CREATION: true,
          DIRECT_LOGIN: true,
          INVITE_ONLY_USER_CREATION: true,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfigInviteOnly');

    cy.wait('@getConfigInviteOnly');
    cy.contains('Invitation required to sign up').should('be.visible');
    cy.contains('Create account').should('not.exist');
  });

  it('Does not show create account for non-Database auth', () => {
    cy.intercept('GET', '/config', {
      body: {
        features: {
          USER_CREATION: true,
          DIRECT_LOGIN: true,
          INVITE_ONLY_USER_CREATION: false,
        },
        config: {
          AUTHENTICATION_TYPE: 'OIDC',
        },
        external_login: [],
      },
    }).as('getConfigOIDC');

    cy.wait('@getConfigOIDC');
    cy.contains("Don't have an account?").should('not.exist');
    cy.contains('Create account').should('not.exist');
  });

  it('Does not show create account when USER_CREATION is false', () => {
    cy.intercept('GET', '/config', {
      body: {
        features: {
          USER_CREATION: false,
          DIRECT_LOGIN: true,
          INVITE_ONLY_USER_CREATION: false,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfigNoUserCreation');

    cy.wait('@getConfigNoUserCreation');
    cy.contains("Don't have an account?").should('not.exist');
    cy.contains('Create account').should('not.exist');
  });
});
