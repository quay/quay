/// <reference types="cypress" />

describe('Tags - Show/Hide Signatures', () => {
  const SHA_DIGEST =
    'sha256-f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4';
  const SIG_TAG = `${SHA_DIGEST}.sig`;
  const SBOM_TAG = `${SHA_DIGEST}.sbom`;
  const ATT_TAG = `${SHA_DIGEST}.att`;

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

  it('hides signature tags by default', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Verify regular tags are visible
    cy.contains('latest').should('be.visible');
    cy.contains('manifestlist').should('be.visible');

    // Verify signature tags are NOT visible by default
    cy.contains(SIG_TAG).should('not.exist');
    cy.contains(SBOM_TAG).should('not.exist');
    cy.contains(ATT_TAG).should('not.exist');
  });

  it('shows signature tags when "Show Signatures" is clicked', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Click the "Show Signatures" button
    cy.contains('button', 'Show Signatures').click();

    // Verify signature tags are now visible
    cy.contains(SIG_TAG).should('be.visible');
    cy.contains(SBOM_TAG).should('be.visible');
    cy.contains(ATT_TAG).should('be.visible');

    // Verify regular tags are still visible
    cy.contains('latest').should('be.visible');
    cy.contains('manifestlist').should('be.visible');

    // Verify button text changed to "Hide Signatures"
    cy.contains('button', 'Hide Signatures').should('be.visible');
  });

  it('hides signature tags when "Hide Signatures" is clicked', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Show signatures first
    cy.contains('button', 'Show Signatures').click();
    cy.contains(SIG_TAG).should('be.visible');

    // Click "Hide Signatures"
    cy.contains('button', 'Hide Signatures').click();

    // Verify signature tags are hidden again
    cy.contains(SIG_TAG).should('not.exist');
    cy.contains(SBOM_TAG).should('not.exist');
    cy.contains(ATT_TAG).should('not.exist');

    // Verify regular tags are still visible
    cy.contains('latest').should('be.visible');
    cy.contains('manifestlist').should('be.visible');

    // Verify button text changed back to "Show Signatures"
    cy.contains('button', 'Show Signatures').should('be.visible');
  });

  it('toggles between show and hide multiple times', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Toggle to show
    cy.contains('button', 'Show Signatures').click();
    cy.contains(SIG_TAG).should('be.visible');
    cy.contains('button', 'Hide Signatures').should('be.visible');

    // Toggle to hide
    cy.contains('button', 'Hide Signatures').click();
    cy.contains(SIG_TAG).should('not.exist');
    cy.contains('button', 'Show Signatures').should('be.visible');

    // Toggle to show again
    cy.contains('button', 'Show Signatures').click();
    cy.contains(SBOM_TAG).should('be.visible');
    cy.contains('button', 'Hide Signatures').should('be.visible');
  });
});
