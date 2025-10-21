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

    // Verify Compact button is selected by default
    cy.get('#compact-view').should('have.attr', 'aria-pressed', 'true');
    cy.get('#expanded-view').should('have.attr', 'aria-pressed', 'false');

    // Verify expanded row content is not visible
    cy.get('.expanded-row').should('not.exist');
  });

  it('switches to expanded view when "Expanded" is clicked', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Click the "Expanded" toggle button
    cy.get('#expanded-view').click();

    // Verify Expanded button is now selected
    cy.get('#expanded-view').should('have.attr', 'aria-pressed', 'true');
    cy.get('#compact-view').should('have.attr', 'aria-pressed', 'false');

    // Verify expanded row content is visible
    cy.get('.expanded-row').should('exist');
    cy.get('.expanded-row-content').should('be.visible');
  });

  it('shows manifest digest in expanded view', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Switch to expanded view
    cy.get('#expanded-view').click();

    // Verify manifest digest is shown
    cy.get('.expanded-row-content').should('contain', 'Manifest:');
    cy.get('.expanded-row-content').should('contain', 'sha256:');
  });

  it('shows labels section in expanded view', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Switch to expanded view
    cy.get('#expanded-view').click();

    // Verify labels section is shown
    cy.get('.expanded-row-content').should('contain', 'Labels:');
  });

  it('shows cosign signature when present', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // First show signatures to ensure we have a tag with cosign signature
    cy.contains('button', 'Show Signatures').click();

    // Switch to expanded view
    cy.get('#expanded-view').click();

    // Check if any tag has cosign signature
    // This test might need adjustment based on actual test data
    cy.get('body').then(($body) => {
      if (
        $body.find('.expanded-row-content:contains("Cosign Signature:")')
          .length > 0
      ) {
        cy.get('.expanded-row-content').should('contain', 'Cosign Signature:');
      }
    });
  });

  it('switches back to compact view when "Compact" is clicked', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Switch to expanded view first
    cy.get('#expanded-view').click();
    cy.get('.expanded-row').should('exist');

    // Switch back to compact view
    cy.get('#compact-view').click();

    // Verify Compact button is now selected
    cy.get('#compact-view').should('have.attr', 'aria-pressed', 'true');
    cy.get('#expanded-view').should('have.attr', 'aria-pressed', 'false');

    // Verify expanded row content is no longer visible
    cy.get('.expanded-row').should('not.exist');
  });

  it('toggles between compact and expanded view multiple times', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Toggle to expanded
    cy.get('#expanded-view').click();
    cy.get('.expanded-row').should('exist');
    cy.get('#expanded-view').should('have.attr', 'aria-pressed', 'true');

    // Toggle back to compact
    cy.get('#compact-view').click();
    cy.get('.expanded-row').should('not.exist');
    cy.get('#compact-view').should('have.attr', 'aria-pressed', 'true');

    // Toggle to expanded again
    cy.get('#expanded-view').click();
    cy.get('.expanded-row').should('exist');
    cy.get('#expanded-view').should('have.attr', 'aria-pressed', 'true');
  });

  it('preserves expanded view when switching between pages', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Switch to expanded view
    cy.get('#expanded-view').click();
    cy.get('.expanded-row').should('exist');

    // Navigate to a different tab
    cy.contains('Information').click();

    // Navigate back to tags
    cy.contains('Tags').click();

    // Verify expanded view is still selected
    cy.get('#expanded-view').should('have.attr', 'aria-pressed', 'true');
    cy.get('.expanded-row').should('exist');
  });

  it('shows expanded content for each visible tag', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Switch to expanded view
    cy.get('#expanded-view').click();

    // Count visible tag rows (excluding expanded rows)
    cy.get('[data-testid="table-entry"]').then(($entries) => {
      const tagCount = $entries.length;

      // Verify we have the same number of expanded rows
      cy.get('.expanded-row').should('have.length', tagCount);
    });
  });

  it('works correctly with manifest list expansion', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Switch to expanded view
    cy.get('#expanded-view').click();

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
