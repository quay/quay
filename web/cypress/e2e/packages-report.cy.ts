/// <reference types="cypress" />

describe('Packages Report Page', () => {
  beforeEach(() => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/tag/?limit=100&page=1&onlyActiveTags=true&specificTag=security',
      {fixture: 'single-tag.json'},
    ).as('getTag');
    cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as('getUser');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
      'getCsrfToken',
    );
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be',
      {fixture: 'manifest.json'},
    ).as('getManifest');
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/labels',
      {fixture: 'labels.json'},
    ).as('getLabels');
  });

  it('render packages', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.contains('Quay Security Reporting has recognized 49 packages');
    cy.contains('Patches are available for 30 vulnerabilities');
    cy.get('[data-testid="packages-chart"]').contains('49').should('exist');
    cy.get('td[data-label="Package Name"]').should('have.length', 20);
  });

  it('render no packages', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/noPackages.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.contains('Quay Security Reporting does not recognize any packages');
    cy.contains('No known patches are available');
    cy.get('[data-testid="packages-chart"]').contains('0').should('exist');
    cy.get('td[data-label="Package Name"]').should('have.length', 0);
  });

  it('filter by name', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.get('td[data-label="Package Name"]').should('have.length', 20);
    cy.get('input[placeholder="Filter Packages..."]').type('python');
    cy.get('td[data-label="Package Name"]').should('have.length', 7);
    cy.get('td[data-label="Package Name"]')
      .filter(':contains("python")')
      .should('have.length', 7);
  });

  it('render unsupported state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/unsupported.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.contains('Security scan is not supported.');
    cy.contains('Image does not have content the scanner recognizes.');
  });

  it('render failed state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/failed.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.contains('Security scan has failed.');
    cy.contains('The scan could not be completed due to error.');
  });

  it('render queued state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/queued.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.contains('Security scan is currently queued.');
    cy.contains('Refresh page for updates in scan status.');
    cy.contains('Reload');
  });

  it('paginate values', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=packages');
    cy.contains('1 - 20 of 49').should('exist');
    cy.get('td[data-label="Package Name"]').should('have.length', 20);

    // Change per page
    cy.get('button:contains("1 - 20 of 49")').first().click();
    cy.contains('20 per page').click();
    cy.get('td[data-label="Package Name"]').should('have.length', 20);

    // cycle through the pages
    cy.get('[id="packages-table-pagination"]').within(() =>
      cy.get('button[aria-label="Go to next page"]').click(),
    );
    cy.get('td[data-label="Package Name"]').should('have.length', 20);
    cy.get('[id="packages-table-pagination"]').within(() =>
      cy.get('button[aria-label="Go to next page"]').click(),
    );
    cy.get('td[data-label="Package Name"]').should('have.length', 9);

    // Go to first page
    cy.get('[id="packages-table-pagination"]').within(() =>
      cy.get('button[aria-label="Go to first page"]').click(),
    );
    cy.contains('libbz2').should('exist');

    // Go to last page
    cy.get('[id="packages-table-pagination"]').within(() =>
      cy.get('button[aria-label="Go to last page"]').click(),
    );
    cy.contains('click').should('exist');

    // Switch per page while while being on a different page
    cy.get('button:contains("41 - 49 of 49")').first().click();
    cy.contains('20 per page').click();
    cy.contains('1 - 20 of 49').should('exist');
    cy.get('td[data-label="Package Name"]').should('have.length', 20);
  });
});
