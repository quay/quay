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

    // Open settings dropdown and enable Show Signatures
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.get('#tags-settings-toggle').click();

    // Verify signature tags are now visible
    cy.contains(SIG_TAG).should('be.visible');
    cy.contains(SBOM_TAG).should('be.visible');
    cy.contains(ATT_TAG).should('be.visible');

    // Verify regular tags are still visible
    cy.contains('latest').should('be.visible');
    cy.contains('manifestlist').should('be.visible');

    // Verify "Show Signatures" checkbox is checked
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures')
      .find('input[type="checkbox"]')
      .should('be.checked');
    cy.get('#tags-settings-toggle').click();
  });

  it('hides signature tags when "Hide Signatures" is clicked', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Show signatures first
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.get('#tags-settings-toggle').click();
    cy.contains(SIG_TAG).should('be.visible');

    // Hide signatures
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.get('#tags-settings-toggle').click();

    // Verify signature tags are hidden again
    cy.contains(SIG_TAG).should('not.exist');
    cy.contains(SBOM_TAG).should('not.exist');
    cy.contains(ATT_TAG).should('not.exist');

    // Verify regular tags are still visible
    cy.contains('latest').should('be.visible');
    cy.contains('manifestlist').should('be.visible');

    // Verify "Show Signatures" checkbox is unchecked
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures')
      .find('input[type="checkbox"]')
      .should('not.be.checked');
    cy.get('#tags-settings-toggle').click();
  });

  it('toggles between show and hide multiple times', () => {
    cy.visit('/repository/user1/hello-world?tab=tags');

    // Toggle to show
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.get('#tags-settings-toggle').click();
    cy.contains(SIG_TAG).should('be.visible');

    // Toggle to hide
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.get('#tags-settings-toggle').click();
    cy.contains(SIG_TAG).should('not.exist');

    // Toggle to show again
    cy.get('#tags-settings-toggle').click();
    cy.contains('[role="menuitem"]', 'Show Signatures').click();
    cy.get('#tags-settings-toggle').click();
    cy.contains(SBOM_TAG).should('be.visible');
  });
});
