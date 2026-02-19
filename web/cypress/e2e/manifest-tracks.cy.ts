/// <reference types="cypress" />

/**
 * Manifest Track Visualization Tests (PROJQUAY-9592)
 *
 * Tests the visual grouping indicators for tags that share the same manifest
 * digest in the tags table. Tags sharing a manifest are connected by colored
 * dots and vertical lines.
 *
 * Uses API mocking to simulate tag responses with controlled manifest digests.
 */

const DIGEST_A =
  'sha256:aaaa111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';
const DIGEST_B =
  'sha256:bbbb111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';
const DIGEST_C =
  'sha256:cccc111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';

const REPO = 'user1/hello-world';

function createMockTag(name: string, digest: string) {
  return {
    name,
    manifest_digest: digest,
    is_manifest_list: false,
    size: 1024,
    last_modified: new Date().toISOString(),
    reversion: false,
    start_ts: Math.floor(Date.now() / 1000),
  };
}

function interceptTagApi(tags: ReturnType<typeof createMockTag>[]) {
  cy.intercept('GET', `/api/v1/repository/${REPO}/tag/*`, {
    statusCode: 200,
    body: {
      tags,
      page: 1,
      has_additional: false,
    },
  }).as('getTags');
}

describe('Manifest Track Visualization', () => {
  beforeEach(() => {
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('shows track column when tags share a manifest digest', () => {
    interceptTagApi([
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_C),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a').should('be.visible');

    cy.get('th[aria-label="Manifest tracks"]').should('be.visible');
  });

  it('hides track column when all tags have unique digests', () => {
    interceptTagApi([
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_B),
      createMockTag('tag-c', DIGEST_C),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a').should('be.visible');

    cy.get('th[aria-label="Manifest tracks"]').should('not.exist');
  });

  it('renders dot buttons only for tags sharing a manifest', () => {
    interceptTagApi([
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_C),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a').should('be.visible');

    // 2 dot buttons for the shared group (one per tag row)
    cy.get('[aria-label*="Select all 2 tags with manifest"]').should(
      'have.length',
      2,
    );

    // The unique tag row should not have a dot button
    cy.get('[data-testid="table-entry"]')
      .filter(':contains("tag-c")')
      .find('[aria-label*="Select all"]')
      .should('not.exist');
  });

  it('clicking dot selects all tags with the same manifest', () => {
    interceptTagApi([
      createMockTag('tag-a1', DIGEST_A),
      createMockTag('tag-a2', DIGEST_A),
      createMockTag('tag-a3', DIGEST_A),
      createMockTag('tag-b1', DIGEST_B),
      createMockTag('tag-b2', DIGEST_B),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a1').should('be.visible');

    // Click the first dot for group A (3 tags sharing DIGEST_A)
    cy.get('[aria-label*="Select all 3 tags with manifest"]').first().click();

    // All group A tags should be checked
    ['tag-a1', 'tag-a2', 'tag-a3'].forEach((tagName) => {
      cy.get('[data-testid="table-entry"]')
        .filter(`:contains("${tagName}")`)
        .find('input[type="checkbox"]')
        .should('be.checked');
    });

    // Group B tags should not be checked
    ['tag-b1', 'tag-b2'].forEach((tagName) => {
      cy.get('[data-testid="table-entry"]')
        .filter(`:contains("${tagName}")`)
        .find('input[type="checkbox"]')
        .should('not.be.checked');
    });

    // Actions button should appear in toolbar
    cy.get('button').contains('Actions').should('be.visible');
  });

  it('dot aria-label conveys tag count and digest prefix', () => {
    interceptTagApi([
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_A),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a').should('be.visible');

    const expectedLabel = `Select all 3 tags with manifest ${DIGEST_A.substring(
      0,
      12,
    )}`;

    cy.get(`[aria-label="${expectedLabel}"]`).should('have.length', 3);

    // Verify the full aria-label value on the first dot
    cy.get(`[aria-label="${expectedLabel}"]`)
      .first()
      .should('have.attr', 'aria-label', expectedLabel);
  });

  it('renders correct dots for multiple track groups', () => {
    interceptTagApi([
      createMockTag('tag-a1', DIGEST_A),
      createMockTag('tag-a2', DIGEST_A),
      createMockTag('tag-a3', DIGEST_A),
      createMockTag('tag-b1', DIGEST_B),
      createMockTag('tag-b2', DIGEST_B),
      createMockTag('tag-b3', DIGEST_B),
      createMockTag('tag-u', DIGEST_C),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a1').should('be.visible');

    // Group A: 3 dots (one per tag sharing DIGEST_A)
    cy.get(
      '[aria-label*="Select all 3 tags with manifest sha256:aaaa1"]',
    ).should('have.length', 3);

    // Group B: 3 dots (one per tag sharing DIGEST_B)
    cy.get(
      '[aria-label*="Select all 3 tags with manifest sha256:bbbb1"]',
    ).should('have.length', 3);

    // Unique tag row has no dot
    cy.get('[data-testid="table-entry"]')
      .filter(':contains("tag-u")')
      .find('[aria-label*="Select all"]')
      .should('not.exist');
  });

  it('unique tag row has no manifest track dot', () => {
    interceptTagApi([
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
      createMockTag('tag-c', DIGEST_C),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-c').should('be.visible');

    cy.get('[data-testid="table-entry"]')
      .filter(':contains("tag-c")')
      .find('.manifest-track-dot')
      .should('not.exist');
  });

  it('supports keyboard activation of track dots', () => {
    interceptTagApi([
      createMockTag('tag-a', DIGEST_A),
      createMockTag('tag-b', DIGEST_A),
    ]);

    cy.visit(`/repository/${REPO}?tab=tags`);
    cy.contains('a', 'tag-a').should('be.visible');

    // Verify accessibility attributes on the dot
    cy.get('[aria-label*="Select all 2 tags with manifest"]')
      .first()
      .should('have.attr', 'role', 'button')
      .and('have.attr', 'tabindex', '0');

    // Activate via keyboard (focus + Enter)
    cy.get('[aria-label*="Select all 2 tags with manifest"]')
      .first()
      .focus()
      .type('{enter}');

    // Both tags should be selected
    ['tag-a', 'tag-b'].forEach((tagName) => {
      cy.get('[data-testid="table-entry"]')
        .filter(`:contains("${tagName}")`)
        .find('input[type="checkbox"]')
        .should('be.checked');
    });
  });
});
