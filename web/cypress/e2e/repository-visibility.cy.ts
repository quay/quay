/// <reference types="cypress" />

describe('Repository Settings - Visibility', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        res.body.features['BILLING'] = true;
        res.body.config['STRIPE_PUBLISHABLE_KEY'] =
          'pk_test_notrealHI2qtSU2DTTO1YZ5qsXlfeGNguyaMCsceSOJmHUxdICvRN5LfNJLah4fTqzlrng3wrXiTeCucQwrf3L6Hd007iruRjQ3';
        return res;
      }),
    ).as('getConfig');
  });

  it('Sets public', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        res.body.features['BILLING'] = false;
        return res;
      }),
    ).as('getConfigNoBilling');
    cy.visit('/repository/user1/nested/repo?tab=settings');
    cy.contains('Repository visibility').click();
    cy.contains(
      'This Repository is currently private. Only users on the permissions list may view and interact with it.',
    ).should('exist');
    cy.contains('Make Public').click();
    cy.contains(
      'This Repository is currently public and is visible to all users, and may be pulled by all users.',
    ).should('exist');
    cy.contains('Make Private').should('exist');
  });

  it('Sets private', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        res.body.features['BILLING'] = false;
        return res;
      }),
    ).as('getConfigNoBilling');
    cy.visit('/repository/projectquay/clair-jwt?tab=settings');
    cy.contains('Repository visibility').click();
    cy.contains(
      'This Repository is currently public and is visible to all users, and may be pulled by all users.',
    ).should('exist');
    cy.contains('Make Private').click();
    cy.contains(
      'This Repository is currently private. Only users on the permissions list may view and interact with it.',
    ).should('exist');
    cy.contains('Make Public').should('exist');
  });

  it('Upgrade plan as user', () => {
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
    cy.intercept('GET', '/api/v1/user/private', {
      privateCount: 1,
      privateAllowed: false,
    }).as('getPrivateRepoCount');
    cy.intercept('GET', '/api/v1/user/plan', {
      hasSubscription: false,
      isExistingCustomer: false,
      plan: 'free',
      usedPrivateRepos: 1,
    }).as('getUserPlan');
    cy.intercept('GET', '/api/v1/user/card', {card: {is_valid: false}}).as(
      'getUserCard',
    );
    cy.intercept(
      'GET',
      'https://api.stripe.com/v1/payment_pages/legacy_bootstrap*',
      {
        ip_location: {
          country_code: 'US',
          precision: 'country',
        },
        livemode: false,
        session_id: 'notreal8-7267-4efd-9782-e1fe233201df',
      },
    ).as('stripeBootstrap');
    cy.intercept('POST', 'https://r.stripe.com/*', {}).as('stripeUpdateR');
    cy.intercept('POST', 'https://m.stripe.com/*', {}).as('stripeUpdateM');
    cy.intercept('GET', 'https://q.stripe.com/*', {}).as('stripeUpdateQ');
    cy.intercept('POST', 'https://api.stripe.com/v1/tokens', {
      id: 'tok_notrealI2qtSU2DTephWdIsy',
    }).as('stripeUpdateTokens');
    cy.intercept('PUT', '/api/v1/user/plan', {statusCode: 201}).as(
      'updateSubscription',
    );
    cy.visit('/repository/user1/hello-world?tab=settings');
    cy.contains('Repository visibility').click();
    cy.contains(
      'This Repository is currently public and is visible to all users, and may be pulled by all users.',
    ).should('exist');
    cy.contains(
      "In order to make this repository private under user1, you will need to upgrade the namespace's plan to at least a Developer plan",
    ).should('exist');
    cy.contains('Upgrade user1').click();
    cy.wait('@stripeBootstrap', {timeout: 27000});
    cy.getIframeBody('iframe[name="stripe_checkout_app"]').within(() => {
      cy.contains('Quay Developer').should('exist');
      cy.contains('Up to 5 private repositories').should('exist');
      cy.contains('user1@redhat.com').should('exist');
      cy.get('input[placeholder="Name"]').type('user1');
      cy.get('input[placeholder="Address"]').type('1 broadway');
      cy.get('#billing-zip').type('10004');
      cy.contains('Payment Info').click();
      cy.get('#card_number').type('4242 4242 4242 4242');
      cy.get('#cc-exp').type('11 / 30');
      cy.get('#cc-csc').type('111');
      cy.contains('Start Trial ($15.00 plan)').click();
    });
    cy.wait('@updateSubscription', {timeout: 25000}).then((xhr) => {
      expect(xhr.request.body.plan).to.equal('personal-2018');
      expect(xhr.request.body.token).to.equal('tok_notrealI2qtSU2DTephWdIsy');
    });
  });

  it('Upgrade plan as organization without card', () => {
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
    cy.intercept('GET', '/api/v1/organization/testorg/private', {
      privateCount: 1,
      privateAllowed: false,
    }).as('getPrivateRepoCount');
    cy.intercept('GET', '/api/v1/organization/testorg/plan', {
      hasSubscription: false,
      isExistingCustomer: false,
      plan: 'free',
      usedPrivateRepos: 1,
    }).as('getUserPlan');
    cy.intercept('GET', '/api/v1/organization/testorg/card', {
      card: {is_valid: false},
    }).as('getUserCard');
    cy.intercept(
      'GET',
      'https://api.stripe.com/v1/payment_pages/legacy_bootstrap*',
      {
        ip_location: {
          country_code: 'US',
          precision: 'country',
        },
        livemode: false,
        session_id: 'notreal8-7267-4efd-9782-e1fe233201df',
      },
    ).as('stripeBootstrap');
    cy.intercept('POST', 'https://r.stripe.com/*', {}).as('stripeUpdateR');
    cy.intercept('POST', 'https://m.stripe.com/*', {}).as('stripeUpdateM');
    cy.intercept('GET', 'https://q.stripe.com/*', {}).as('stripeUpdateQ');
    cy.intercept('POST', 'https://api.stripe.com/v1/tokens', {
      id: 'tok_notrealI2qtSU2DTephWdIsy',
    }).as('stripeUpdateTokens');
    cy.intercept('PUT', '/api/v1/organization/testorg/plan', {
      statusCode: 201,
    }).as('updateSubscription');
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Repository visibility').click();
    cy.contains(
      'This Repository is currently public and is visible to all users, and may be pulled by all users.',
    ).should('exist');
    cy.contains(
      "In order to make this repository private under testorg, you will need to upgrade the namespace's plan to at least a Micro plan",
    ).should('exist');
    cy.contains('Upgrade testorg').click();
    cy.wait('@stripeBootstrap', {timeout: 27000});
    cy.getIframeBody('iframe[name="stripe_checkout_app"]').within(() => {
      cy.contains('Quay Micro Subscription').should('exist');
      cy.contains('Up to 10 private repositories').should('exist');
      cy.contains('user1@redhat.com').should('exist');
      cy.get('input[placeholder="Name"]').type('user1');
      cy.get('input[placeholder="Address"]').type('1 broadway');
      cy.get('#billing-zip').type('10004');
      cy.contains('Payment Info').click();
      cy.get('#card_number').type('4242 4242 4242 4242');
      cy.get('#cc-exp').type('11 / 30');
      cy.get('#cc-csc').type('111');
      cy.contains('Start Trial ($30.00 plan)').click();
    });
    cy.wait('@updateSubscription', {timeout: 25000}).then((xhr) => {
      expect(xhr.request.body.plan).to.equal('bus-micro-2018');
      expect(xhr.request.body.token).to.equal('tok_notrealI2qtSU2DTephWdIsy');
    });
  });

  it('Upgrade plan as organization from existing plan', () => {
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
    cy.intercept('GET', '/api/v1/organization/testorg/private', {
      privateCount: 20,
      privateAllowed: false,
    }).as('getPrivateRepoCount');
    cy.intercept('GET', '/api/v1/organization/testorg/plan', {
      hasSubscription: true,
      isExistingCustomer: true,
      plan: 'bus-small-2018',
      usedPrivateRepos: 20,
    }).as('getUserPlan');
    cy.intercept('GET', '/api/v1/organization/testorg/card', {
      card: {is_valid: true, last4: '4242'},
    }).as('getUserCard');
    cy.intercept('PUT', '/api/v1/organization/testorg/plan', {
      statusCode: 201,
    }).as('updateSubscription');
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Repository visibility').click();
    cy.contains(
      'This Repository is currently public and is visible to all users, and may be pulled by all users.',
    ).should('exist');
    cy.contains(
      "In order to make this repository private under testorg, you will need to upgrade the namespace's plan to at least a Medium plan",
    ).should('exist');
    cy.contains('Upgrade testorg').click();
    cy.wait('@updateSubscription', {timeout: 25000}).then((xhr) => {
      expect(xhr.request.body.plan).to.equal('bus-medium-2018');
      expect(xhr.request.body.token).to.be.undefined;
    });
  });

  it('Max private repo limit hit', () => {
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
    cy.intercept('GET', '/api/v1/organization/testorg/private', {
      privateCount: 15000,
      privateAllowed: false,
    }).as('getPrivateRepoCount');
    cy.intercept('GET', '/api/v1/organization/testorg/plan', {
      hasSubscription: true,
      isExistingCustomer: true,
      plan: 'price_1LRztA2OoNF1TIf0SvSrz106',
      usedPrivateRepos: 15000,
    }).as('getUserPlan');
    cy.intercept('GET', '/api/v1/organization/testorg/card', {
      card: {is_valid: true, last4: '4242'},
    }).as('getUserCard');
    cy.intercept('PUT', '/api/v1/organization/testorg/plan', {
      statusCode: 201,
    }).as('updateSubscription');
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Repository visibility').click();
    cy.contains(
      'This Repository is currently public and is visible to all users, and may be pulled by all users.',
    ).should('exist');
    cy.contains(
      'This organization has reached its private repository limit. Please contact your administrator.',
    ).should('exist');
    cy.contains('Upgrade testorg').should('not.exist');
  });
});
