/// <reference types="cypress" />

describe('Footer', () => {
  beforeEach(() => {
    cy.visit('/signin');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });

    // Default config intercept (tests can override by setting their own)
    cy.fixture('config.json').then((config) => {
      cy.intercept('GET', '/config', config).as('getConfig');
    });
  });

  it('displays footer with version and documentation link', () => {
    cy.visit('/organization');
    cy.wait('@getConfig');

    // Check that footer is visible
    cy.get('#quay-footer').should('be.visible');

    // Check that footer container exists
    cy.get('.quay-footer-container').should('exist');

    // Check that footer list exists
    cy.get('.quay-footer-list').should('exist');

    // Check that documentation link is present
    cy.get('.quay-footer-list')
      .contains('a', 'Documentation')
      .should('have.attr', 'href')
      .and('include', 'docs.projectquay.io');

    // Check that version number is displayed on the left
    cy.get('.quay-footer-version').should('be.visible');
    cy.get('.quay-footer-version').should('contain', 'Quay');
  });

  it('documentation link opens in new tab', () => {
    cy.visit('/organization');
    cy.wait('@getConfig');

    // Check that documentation link has correct attributes
    cy.get('.quay-footer-list')
      .contains('a', 'Documentation')
      .should('have.attr', 'target', '_blank')
      .and('have.attr', 'rel', 'noopener noreferrer');
  });

  it('footer is visible on different pages', () => {
    // Check on organization page
    cy.visit('/organization');
    cy.wait('@getConfig');
    cy.get('#quay-footer').should('be.visible');

    // Check on repositories page
    cy.visit('/repository');
    cy.get('#quay-footer').should('be.visible');
  });

  it('footer contains all configured links', () => {
    cy.fixture('config.json').then((config) => {
      // Add footer links configuration
      config.config.FOOTER_LINKS = {
        TERMS_OF_SERVICE_URL: 'https://example.com/terms',
        PRIVACY_POLICY_URL: 'https://example.com/privacy',
        SECURITY_URL: 'https://example.com/security',
        ABOUT_URL: 'https://example.com/about',
      };
      cy.intercept('GET', '/config', config).as('getConfigWithFooterLinks');
    });

    cy.visit('/organization');
    cy.wait('@getConfigWithFooterLinks');

    // Check that configured footer links are present
    cy.get('.quay-footer-list')
      .contains('a', 'Terms of Service')
      .should('exist');
    cy.get('.quay-footer-list').contains('a', 'Privacy').should('exist');
    cy.get('.quay-footer-list').contains('a', 'Security').should('exist');
    cy.get('.quay-footer-list').contains('a', 'About').should('exist');
  });

  it('footer image link is displayed when configured', () => {
    cy.fixture('config.json').then((config) => {
      // Add footer image configuration
      config.config.BRANDING = {
        logo: '/static/img/quay-horizontal-color.svg',
        footer_img: '/static/img/RedHat.svg',
        footer_url:
          'https://access.redhat.com/documentation/en-us/red_hat_quay/3/',
      };
      cy.intercept('GET', '/config', config).as('getConfigWithFooterImg');
    });

    cy.visit('/organization');
    cy.wait('@getConfigWithFooterImg');

    // Check that footer image link exists
    cy.get('.quay-footer-container')
      .find('a')
      .should('have.attr', 'href')
      .and('include', 'access.redhat.com');

    // Check that footer image exists
    cy.get('.quay-footer-container')
      .find('img')
      .should('have.attr', 'src')
      .and('include', 'RedHat.svg');

    // Check that link opens in new tab
    cy.get('.quay-footer-container')
      .find('a')
      .should('have.attr', 'target', '_blank')
      .and('have.attr', 'rel', 'noopener noreferrer');
  });

  it('footer image is displayed without link when footer_url not configured', () => {
    cy.fixture('config.json').then((config) => {
      // Add footer image without URL
      config.config.BRANDING = {
        logo: '/static/img/quay-horizontal-color.svg',
        footer_img: '/static/img/RedHat.svg',
        footer_url: null,
      };
      cy.intercept('GET', '/config', config).as('getConfigWithFooterImgNoUrl');
    });

    cy.visit('/organization');
    cy.wait('@getConfigWithFooterImgNoUrl');

    // Check that footer image exists
    cy.get('.quay-footer-container')
      .find('img')
      .should('have.attr', 'src')
      .and('include', 'RedHat.svg');

    // Check that no link wraps the image (image is direct child of container)
    cy.get('.quay-footer-container')
      .find('img')
      .parent()
      .should('not.match', 'a');
  });

  it('service status is displayed for quay.io with BILLING', () => {
    cy.fixture('config.json').then((config) => {
      config.config.SERVER_HOSTNAME = 'quay.io';
      config.features.BILLING = true;
      cy.intercept('GET', '/config', config).as('getConfigQuayIO');
    });

    cy.visit('/organization');
    cy.wait('@getConfigQuayIO');

    // Service status component should be rendered
    // (actual status behavior is tested in UseServiceStatus hook tests)
    cy.get('.quay-footer-list li').should('have.length.at.least', 1);
  });

  it('TrustArc widget container is displayed for quay.io with BILLING', () => {
    cy.fixture('config.json').then((config) => {
      config.config.SERVER_HOSTNAME = 'quay.io';
      config.features.BILLING = true;
      cy.intercept('GET', '/config', config).as('getConfigQuayIO');
    });

    cy.visit('/organization');
    cy.wait('@getConfigQuayIO');

    // Check that TrustArc container exists
    cy.get('#teconsent').should('exist');
  });

  it('TrustArc consent blackbar is displayed for quay.io', () => {
    cy.fixture('config.json').then((config) => {
      config.config.SERVER_HOSTNAME = 'quay.io';
      cy.intercept('GET', '/config', config).as('getConfigQuayIO');
    });

    cy.visit('/organization');
    cy.wait('@getConfigQuayIO');

    // Check that consent blackbar exists
    cy.get('#consent_blackbar').should('exist');
    cy.get('#consent_blackbar').should('have.css', 'position', 'fixed');
    cy.get('#consent_blackbar').should('have.css', 'bottom', '0px');
  });

  it('service status and TrustArc are not displayed for non-quay.io', () => {
    cy.visit('/organization');
    cy.wait('@getConfig');

    // Check that service status icon does not exist
    cy.get('.service-status-icon').should('not.exist');

    // Check that TrustArc container does not exist
    cy.get('#teconsent').should('not.exist');

    // Check that consent blackbar does not exist
    cy.get('#consent_blackbar').should('not.exist');
  });
});
