/// <reference types="cypress" />

describe('External Scripts Loading (PROJQUAY-9803)', () => {
  beforeEach(() => {
    // Seed database for each test to ensure isolation
    cy.exec('npm run quay:seed');

    // Login for all tests
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  /**
   * Test that external scripts (Stripe, StatusPage) are NOT loaded when BILLING feature is disabled.
   * This is the default configuration for on-premise deployments and prevents 85-second delays
   * in air-gapped/restricted network environments.
   */
  describe('BILLING Feature Disabled (Default)', () => {
    beforeEach(() => {
      // Explicitly disable BILLING in config
      cy.fixture('config.json').then((config) => {
        config.features.BILLING = false;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
        'getCsrfToken',
      );
      cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as(
        'getUser',
      );
    });

    it('should NOT load Stripe checkout script when BILLING is disabled', () => {
      cy.visit('/');
      cy.wait(['@getConfig', '@getCsrfToken', '@getUser']);

      // Verify the script tag with ID 'stripe-checkout' does not exist in the DOM
      cy.get('#stripe-checkout').should('not.exist');

      // Verify the script is not in the document head
      cy.document().then((doc) => {
        const scripts = Array.from(doc.querySelectorAll('script'));
        const stripeScript = scripts.find((script) =>
          script.src.includes('checkout.stripe.com'),
        );
        expect(stripeScript).to.be.undefined;
      });
    });

    it('should NOT load StatusPage widget script when BILLING is disabled', () => {
      cy.visit('/');
      cy.wait(['@getConfig', '@getCsrfToken', '@getUser']);

      // Verify the script tag with ID 'statuspage-widget' does not exist in the DOM
      cy.get('#statuspage-widget').should('not.exist');

      // Verify the script is not in the document head
      cy.document().then((doc) => {
        const scripts = Array.from(doc.querySelectorAll('script'));
        const statuspageScript = scripts.find((script) =>
          script.src.includes('cdn.statuspage.io'),
        );
        expect(statuspageScript).to.be.undefined;
      });
    });

    it('should NOT make external network requests to stripe.com or statuspage.io', () => {
      cy.visit('/');
      cy.wait(['@getConfig', '@getCsrfToken', '@getUser']);

      // Wait for a reasonable time to ensure no delayed script loading
      cy.wait(2000);

      // Verify no network requests were made to external domains
      cy.window().then((win) => {
        // Check window.performance for resource timing entries
        const resources = win.performance.getEntriesByType('resource');
        const externalRequests = resources.filter((entry: PerformanceEntry) => {
          const resource = entry as PerformanceResourceTiming;
          return (
            resource.name.includes('stripe.com') ||
            resource.name.includes('statuspage.io')
          );
        });
        expect(externalRequests).to.have.length(0);
      });
    });
  });

  /**
   * Test that external scripts ARE loaded when BILLING feature is enabled.
   * This simulates quay.io production environment where billing features are active.
   */
  describe('BILLING Feature Enabled', () => {
    beforeEach(() => {
      // Mock config with BILLING enabled
      cy.fixture('config.json').then((config) => {
        config.features.BILLING = true;
        cy.intercept('GET', '/config', config).as('getConfigWithBilling');
      });

      // Intercept external script requests to prevent actual loading
      cy.intercept('GET', '**/checkout.stripe.com/**', {
        statusCode: 200,
        body: '// Mock Stripe script',
      }).as('getStripeScript');

      cy.intercept('GET', '**/cdn.statuspage.io/**', {
        statusCode: 200,
        body: '// Mock StatusPage script',
      }).as('getStatuspageScript');
    });

    it('should load Stripe checkout script when BILLING is enabled', () => {
      cy.visit('/organization');
      cy.wait('@getConfigWithBilling');

      // Wait for the script to be injected
      cy.wait('@getStripeScript', {timeout: 10000});

      // Verify the script tag exists in the DOM
      cy.get('#stripe-checkout', {timeout: 10000}).should('exist');

      // Verify the script has async attribute
      cy.get('#stripe-checkout').should('have.attr', 'async');

      // Verify the script src is correct
      cy.get('#stripe-checkout').should(
        'have.attr',
        'src',
        'https://checkout.stripe.com/checkout.js',
      );
    });

    it('should load StatusPage widget script when BILLING is enabled', () => {
      cy.visit('/organization');
      cy.wait('@getConfigWithBilling');

      // Wait for the script to be injected
      cy.wait('@getStatuspageScript', {timeout: 10000});

      // Verify the script tag exists in the DOM
      cy.get('#statuspage-widget', {timeout: 10000}).should('exist');

      // Verify the script has async attribute
      cy.get('#statuspage-widget').should('have.attr', 'async');

      // Verify the script src is correct
      cy.get('#statuspage-widget').should(
        'have.attr',
        'src',
        'https://cdn.statuspage.io/se-v2.js',
      );
    });
  });
});
