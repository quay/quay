/// <reference types="cypress" />

describe('Account Settings Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
  });

  it('Theme switcher', () => {
    cy.visit('/overview');

    // Check if the default theme is light
    cy.get('html').should('not.have.class', 'pf-v5-theme-dark');

    // Ensure the theme switcher is present
    cy.get('[id=user-menu-toggle]').click();
    cy.get('#toggle-group-light-theme').should('exist');
    cy.get('#toggle-group-dark-theme').should('exist');
    cy.get('#toggle-group-auto-theme').should('exist');

    // Ensure the theme switcher is set to auto
    cy.get('#toggle-group-auto-theme').should('have.class', 'pf-m-selected');
  });

  it('Switch themes', () => {
    cy.visit('/overview');

    // Check if the default theme is light
    cy.get('html').should('not.have.class', 'pf-v5-theme-dark');

    // Switch to dark theme
    cy.get('[id=user-menu-toggle]').click();
    cy.get('#toggle-group-dark-theme').click();

    // Ensure the theme is set to dark
    cy.get('#toggle-group-dark-theme').should('have.class', 'pf-m-selected');
    cy.get('html').should('have.class', 'pf-v5-theme-dark');

    // Ensure local preference is saved
    cy.window().then((window) => {
      expect(window.localStorage.getItem('theme-preference')).to.equal('DARK');
    });

    // Ensure preference used on load
    cy.reload();
    cy.get('html').should('have.class', 'pf-v5-theme-dark');

    // Ensure the theme switcher respects local preference
    cy.get('[id=user-menu-toggle]').click();
    cy.get('#toggle-group-dark-theme').should('have.class', 'pf-m-selected');

    // Switch to light theme
    cy.get('#toggle-group-light-theme').click();

    // Ensure the theme is set to light
    cy.get('#toggle-group-light-theme').should('have.class', 'pf-m-selected');
    cy.get('html').should('not.have.class', 'pf-v5-theme-dark');

    // Ensure local preference is saved
    cy.window().then((window) => {
      expect(window.localStorage.getItem('theme-preference')).to.equal('LIGHT');
    });
  });

  it('Theme switcher with browser in dark mode', () => {
    cy.wrap(
      Cypress.automation('remote:debugger:protocol', {
        command: 'Emulation.setEmulatedMedia',
        params: {
          media: 'page',
          features: [
            {
              name: 'prefers-color-scheme',
              value: 'dark',
            },
          ],
        },
      }),
    );

    cy.visit('/overview');

    // Check if the default theme is dark
    cy.get('html').should('have.class', 'pf-v5-theme-dark');

    // Ensure the theme switcher is present
    cy.get('[id=user-menu-toggle]').click();

    // Ensure the theme switcher is set to auto and reacts to live changes in the browser preferences
    cy.get('#toggle-group-auto-theme')
      .should('have.class', 'pf-m-selected')
      .then(() => {
        return Cypress.automation('remote:debugger:protocol', {
          command: 'Emulation.setEmulatedMedia',
          params: {
            media: 'page',
            features: [
              {
                name: 'prefers-color-scheme',
                value: 'light',
              },
            ],
          },
        });
      })
      .then(() => {
        cy.get('html').should('not.have.class', 'pf-v5-theme-dark');
      });
  });
});
