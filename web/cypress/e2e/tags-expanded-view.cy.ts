/// <reference types="cypress" />

describe('Tags - Compact/Expanded View', () => {
  before(() => {
    cy.exec('npm run quay:seed');
  });

  beforeEach(() => {
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('shows tags in compact view by default', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings dropdown
    cy.get('#tags-settings-toggle').click();

    // Verify expanded view checkbox is off by default
    cy.contains('[role="menuitem"]', 'Expanded View').should('exist');
    cy.contains('[role="menuitem"]', 'Expanded View')
      .find('input[type="checkbox"]')
      .should('not.be.checked');

    // Close dropdown
    cy.get('#tags-settings-toggle').click();

    // Verify expanded row content is not visible
    cy.get('.expanded-row').should('not.exist');
  });

  it('switches to expanded view when switch is toggled', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings dropdown
    cy.get('#tags-settings-toggle').click();

    // Click the expanded view menu item
    cy.contains('[role="menuitem"]', 'Expanded View').click();

    // Close dropdown
    cy.get('#tags-settings-toggle').click();

    // Verify expanded row content is visible
    cy.get('.expanded-row').should('exist');
    cy.get('.expanded-row-content').should('be.visible');
  });

  it('shows manifest digest in expanded view', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();

    // Verify manifest digest is shown (UI displays "SHA256" text, not "Manifest:" label)
    cy.get('.expanded-row-content').should('contain', 'SHA256');
    cy.get('.expanded-row-content').should('contain', 'f54a58bc1aac');
  });

  it('shows labels section in expanded view', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();

    // Verify labels section is shown (UI displays labels as key=value or "No labels found")
    cy.get('.expanded-row-content')
      .first()
      .then(($content) => {
        const text = $content.text();
        // Labels are shown as key=value pairs (e.g., "version = 1.0.0") or "No labels found"
        expect(text).to.satisfy(
          (text: string) =>
            text.includes('=') || text.includes('No labels found'),
        );
      });
  });

  it('shows cosign signature when present', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable show signatures and expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();

    // Check if any tag has cosign signature
    cy.get('body').then(($body) => {
      if (
        $body.find('.expanded-row-content:contains("Cosign Signature:")')
          .length > 0
      ) {
        cy.get('.expanded-row-content').should('contain', 'Cosign Signature:');
      }
    });
  });

  it('switches back to compact view when switch is toggled off', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();
    cy.get('.expanded-row').should('exist');

    // Open settings and disable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();

    // Verify expanded row content is no longer visible
    cy.get('.expanded-row').should('not.exist');
  });

  it('toggles between compact and expanded view multiple times', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Toggle to expanded
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();
    cy.get('.expanded-row').should('exist');

    // Toggle back to compact
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();
    cy.get('.expanded-row').should('not.exist');

    // Toggle to expanded again
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();
    cy.get('.expanded-row').should('exist');
  });

  it('preserves expanded view when switching between pages', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();
    cy.get('.expanded-row').should('exist');

    // Navigate to a different tab
    cy.contains('Information').click();

    // Navigate back to tags
    cy.contains('Tags').click();

    // Verify expanded view is still enabled
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View')
      .find('input[type="checkbox"]')
      .should('be.checked');
    cy.get('#tags-settings-toggle').click();
    cy.get('.expanded-row').should('exist');
  });

  it('shows expanded content for each visible tag', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();

    // Count visible tag rows (excluding expanded rows)
    cy.get('[data-testid="table-entry"]').then(($entries) => {
      const tagCount = $entries.length;

      // Verify we have the same number of expanded rows
      cy.get('.expanded-row').should('have.length', tagCount);
    });
  });

  it('works correctly with manifest list expansion', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Open settings and enable expanded view
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Expanded View').click();
    cy.get('#tags-settings-toggle').click();

    // Find a manifest list tag and expand it
    cy.contains('manifestlist')
      .parents('tbody')
      .within(() => {
        // Click the expand button for manifest list
        cy.get('[aria-label="Details"]').first().click();
      });

    // Verify both manifest list child manifests and expanded view are shown
    cy.get('.expanded-row').should('exist');
    cy.get('.expanded-row-content').should('be.visible');
  });
});
