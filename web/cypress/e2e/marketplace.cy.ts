const marketplaceOrgResponse = [
  {
    id: 1,
    subscription_id: 12345678,
    user_id: 36,
    org_id: 37,
    quantity: 2,
    sku: 'MW02701',
    metadata: {
      title: 'premium',
      privateRepos: 9007199254740991,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02701',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
];

const marketplaceUnlimitedResponse = [
  {
    id: 1,
    subscription_id: 12345678,
    user_id: 36,
    org_id: 37,
    quantity: 2,
    sku: 'MW02702',
    metadata: {
      title: 'premium',
      privateRepos: 9007199254740991,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02702',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
];

const marketplaceUserResponse = [
  {
    id: 12345678,
    masterEndSystemName: 'Quay',
    createdEndSystemName: 'SUBSCRIPTION',
    createdDate: 1675957362000,
    lastUpdateEndSystemName: 'SUBSCRIPTION',
    lastUpdateDate: 1675957362000,
    installBaseStartDate: 1707368400000,
    installBaseEndDate: 1707368399000,
    webCustomerId: 123456,
    subscriptionNumber: '12399889',
    quantity: 2,
    effectiveStartDate: 1707368400000,
    effectiveEndDate: 3813177600,
    sku: 'MW02701',
    assigned_to_org: null,
    metadata: {
      title: 'premium',
      privateRepos: 100,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02701',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
  {
    id: 11223344,
    masterEndSystemName: 'Quay',
    createdEndSystemName: 'SUBSCRIPTION',
    createdDate: 1675957362000,
    lastUpdateEndSystemName: 'SUBSCRIPTION',
    lastUpdateDate: 1675957362000,
    installBaseStartDate: 1707368400000,
    installBaseEndDate: 1707368399000,
    webCustomerId: 123456,
    subscriptionNumber: '12399889',
    quantity: 1,
    effectiveStartDate: 1707368400000,
    effectiveEndDate: 3813177600,
    sku: 'MW02701',
    assigned_to_org: null,
    metadata: {
      title: 'premium',
      privateRepos: 100,
      stripeId: 'not_a_stripe_plan',
      rh_sku: 'MW02701',
      sku_billing: true,
      plans_page_hidden: true,
    },
  },
];

const plansResponse = {
  hasSubscription: false,
  isExistingCustomer: true,
  plan: 'free',
  usedPrivateRepos: 0,
};
const privateResponse = {
  privateAllowed: true,
  privateCount: 0,
};

describe('Marketplace Section', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('ListSubscriptions', () => {
    cy.intercept('GET', '/api/v1/user/marketplace', marketplaceUserResponse);
    cy.intercept('GET', '/api/v1/user/private', privateResponse);
    cy.intercept('GET', '/api/v1/user/plan', plansResponse);
    cy.visit('/organization/user1?tab=Settings');
    cy.get('#pf-tab-1-billinginformation').click();
    cy.get('#user-subscription-list').contains(
      '2x MW02701 belonging to user namespace',
    );
    cy.get('#user-subscription-list').contains(
      '1x MW02701 belonging to user namespace',
    );
  });

  it('ManageSubscription', () => {
    cy.intercept('GET', '/api/v1/plans', {fixture: 'plans.json'});
    cy.intercept('GET', '/api/v1/user/private', privateResponse);
    cy.intercept('GET', '/api/v1/user/plan', plansResponse);
    cy.intercept('GET', '/api/v1/organization/projectquay/plan', plansResponse);
    cy.intercept('GET', '/api/v1/user/marketplace', marketplaceUserResponse);
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/marketplace',
      marketplaceOrgResponse,
    );
    cy.intercept(
      'POST',
      '/api/v1/organization/projectquay/marketplace',
      'Okay',
    );
    cy.intercept(
      'POST',
      '/api/v1/organization/projectquay/marketplace/batchremove',
      'Okay',
    );

    cy.visit('/organization/projectquay?tab=Settings');
    cy.get('#pf-tab-1-billinginformation').click();
    cy.get('#attach-subscription-button').click();
    cy.get('#subscription-select-toggle').click();
    cy.get('#subscription-select-list').contains('2x MW02701').click();
    cy.get('#confirm-subscription-select').click();
    cy.contains('Successfully attached subscription').should('exist');

    cy.get('#remove-subscription-button').click();
    cy.get('#subscription-select-toggle').click();
    cy.get('#subscription-select-list').contains('2x MW02701').click();
    cy.get('#confirm-subscription-select').click();
    cy.contains('Successfully removed subscription').should('exist');
  });

  it('ViewUnlimitedSubscriptions', () => {
    cy.intercept('GET', '/api/v1/plans', {fixture: 'plans.json'});
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/marketplace',
      marketplaceUnlimitedResponse,
    );
    cy.intercept('GET', '/api/v1/user/marketplace', marketplaceUserResponse);
    cy.intercept('GET', '/api/v1/user/private', privateResponse);
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/private',
      privateResponse,
    );
    cy.intercept('GET', '/api/v1/user/plan', plansResponse);
    cy.intercept('GET', '/api/v1/organization/projectquay/plan', plansResponse);

    cy.visit('/organization/projectquay?tab=Settings');
    cy.get('#pf-tab-1-billinginformation').click();
    cy.get('#form-form')
      .contains('0 of unlimited private repositories used')
      .should('exist');
  });
});
