describe('System Status Banner', () => {
  beforeEach(() => {
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Read-only mode banner', () => {
    it('displays read-only banner when registry_state is readonly', () => {
      // Mock config with read-only mode enabled
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.registry_state = 'readonly';
          return res;
        }),
      ).as('getConfig');

      cy.visit('/organization');
      cy.wait('@getConfig');

      // Verify banner is visible
      cy.get('[data-testid="readonly-mode-banner"]').should('be.visible');

      // Verify banner contains expected text
      cy.get('[data-testid="readonly-mode-banner"]').should(
        'contain',
        'is currently in read-only mode',
      );
      cy.get('[data-testid="readonly-mode-banner"]').should(
        'contain',
        'Pulls and other read-only operations will succeed',
      );
      cy.get('[data-testid="readonly-mode-banner"]').should(
        'contain',
        'all other operations are currently suspended',
      );
    });

    it('does not display read-only banner in normal mode', () => {
      cy.visit('/organization');

      // Verify banner is not present
      cy.get('[data-testid="readonly-mode-banner"]').should('not.exist');
    });

    it('displays registry name in the banner', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.registry_state = 'readonly';
          return res;
        }),
      ).as('getConfig');

      cy.visit('/organization');
      cy.wait('@getConfig');

      // Verify registry name is displayed (from config)
      cy.get('[data-testid="readonly-mode-banner"]')
        .invoke('text')
        .should('match', /\S+\s+is currently in read-only mode/);
    });
  });

  describe('Account recovery mode banner', () => {
    it('displays account recovery banner when account_recovery_mode is true', () => {
      // Mock config with account recovery mode enabled
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.account_recovery_mode = true;
          return res;
        }),
      ).as('getConfig');

      cy.visit('/organization');
      cy.wait('@getConfig');

      // Verify banner is visible
      cy.get('[data-testid="account-recovery-mode-banner"]').should(
        'be.visible',
      );

      // Verify banner contains expected text
      cy.get('[data-testid="account-recovery-mode-banner"]').should(
        'contain',
        'is currently in account recovery mode',
      );
      cy.get('[data-testid="account-recovery-mode-banner"]').should(
        'contain',
        'This instance should only be used to link accounts',
      );
      cy.get('[data-testid="account-recovery-mode-banner"]').should(
        'contain',
        'Registry operations such as pushes/pulls will not work',
      );
    });

    it('does not display account recovery banner in normal mode', () => {
      // Config defaults to account_recovery_mode: false, no intercept needed
      cy.visit('/organization');

      // Verify banner is not present
      cy.get('[data-testid="account-recovery-mode-banner"]').should(
        'not.exist',
      );
    });
  });

  describe('Banner positioning', () => {
    it('displays correctly in page layout', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.registry_state = 'readonly';
          return res;
        }),
      ).as('getConfig');

      cy.visit('/organization');
      cy.wait('@getConfig');

      // The read-only banner should be visible in the page
      cy.get('[data-testid="readonly-mode-banner"]')
        .should('be.visible')
        .parent()
        .should('exist');
    });
  });

  describe('Both banners', () => {
    it('displays both banners when both modes are active', () => {
      // Create a config with both flags enabled
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.registry_state = 'readonly';
          res.body.account_recovery_mode = true;
          return res;
        }),
      ).as('getConfig');

      cy.visit('/organization');
      cy.wait('@getConfig');

      // Verify both banners are visible
      cy.get('[data-testid="readonly-mode-banner"]').should('be.visible');
      cy.get('[data-testid="account-recovery-mode-banner"]').should(
        'be.visible',
      );
    });
  });

  describe('Multiple page navigation', () => {
    it('displays banner across different pages', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.registry_state = 'readonly';
          return res;
        }),
      ).as('getConfig');

      // Visit organization page
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.get('[data-testid="readonly-mode-banner"]').should('be.visible');

      // Navigate to repositories page
      cy.visit('/repository');
      cy.get('[data-testid="readonly-mode-banner"]').should('be.visible');

      // Navigate to overview page
      cy.visit('/overview');
      cy.get('[data-testid="readonly-mode-banner"]').should('be.visible');
    });
  });
});
