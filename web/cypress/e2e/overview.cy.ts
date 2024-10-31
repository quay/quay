describe('Overview List Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.visit('/overview');
  });

  it('Dropdowns', () => {
    cy.visit('/overview');
    cy.get('#store-containers-dropdown').click();

    cy.get('#store-containers-info').should('be.visible');

    cy.get('#build-containers-dropdown').click();
    cy.get('#build-containers-info').should('be.visible');

    cy.get('#scan-containers-dropdown').click();
    cy.get('#scan-containers-info').should('be.visible');

    cy.get('#public-containers-dropdown').click();
    cy.get('#public-containers-info').should('be.visible');
  });

  it('External Links', () => {
    cy.visit('/overview');

    cy.get('#try-quayio-button').click();
    cy.location('pathname').should('eq', '/organization');

    cy.visit('/overview');

    cy.get('#purchase-quayio-button').click();
    cy.get('#purchase-plans').should('be.visible');
  });

  it('Tabs', () => {
    cy.visit('/overview');
    cy.get('#pf-tab-1-pricing-tab').click();
    cy.get('#purchase-plans').should('be.visible');

    cy.get('#pf-tab-0-overview-tab').click();
    cy.get('#store-containers-dropdown').should('be.visible');
  });

  it('Purchase Plans', () => {
    const options = [
      '#medium',
      '#large',
      '#XL',
      '#XXL',
      '#XXXL',
      '#XXXXL',
      '#XXXXXL',
    ];
    cy.visit('/overview');
    cy.get('#pf-tab-1-pricing-tab').click();

    options.forEach((option) => {
      cy.get('#plans-dropdown').click();
      cy.get(option).click();
      cy.get('#selected-pricing')
        .scrollIntoView()
        .should('be.visible')
        .then(($selectedPricing) => {
          const selectedPricingText = $selectedPricing.text();
          const pricingValue = selectedPricingText.split(' - ')[1];
          cy.get('#pricing-value').should(
            'contain',
            pricingValue.concat('nth'),
          );
        });
    });
  });
});
