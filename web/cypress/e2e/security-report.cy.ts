/// <reference types="cypress" />

import _ from 'lodash';

describe('Security Report Page', () => {
  before(() => {
    cy.exec('npm run quay:seed');
  });

  beforeEach(() => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/tag/?limit=100&page=1&onlyActiveTags=true&specificTag=security',
      {fixture: 'single-tag.json'},
    ).as('getTag');
    cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as('getUser');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
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

  it('render no vulnerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/noVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.contains(
      'Quay Security Reporting has detected no vulnerabilities',
    ).should('exist');
    cy.get('[data-testid="vulnerability-chart"]').within(() =>
      cy.contains('0'),
    );
    cy.get('td[data-label="Advisory"]').should('have.length', 0);
  });

  it('render mixed vulnerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.contains(
      'Quay Security Reporting has detected 39 vulnerabilities',
    ).should('exist');
    cy.contains(
      '2 vulnerabilities are suppressed by the repository and manifest settings',
    ).should('exist');
    cy.contains('Patches are available for 30 vulnerabilities').should('exist');
    cy.get('[data-testid="vulnerability-chart"]').within(() =>
      cy.contains('39'),
    );
    cy.get('td[data-label="Advisory"]').should('have.length', 20);

    cy.get('button:contains("1 - 20 of 39")').first().click();
    cy.contains('100 per page').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 39);
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('[data-label="Severity"]')
        .get('span:contains("Critical")')
        .should('have.length', 3);
      cy.get('[data-label="Severity"]')
        .get('span:contains("High")')
        .should('have.length', 12);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Medium")')
        .should('have.length', 22);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Low")')
        .should('have.length', 1);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Unknown")')
        .should('have.length', 1);
    });
  });

  it('only show fixable', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('button:contains("1 - 20 of 39")').first().click();
    cy.contains('100 per page').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 39);
    cy.get('#fixable-checkbox').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 29);
    cy.contains('(None)').should('not.exist');
    cy.get('#fixable-checkbox').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 39);
  });

  it('filter by name', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('input[placeholder="Filter Vulnerabilities..."]').type('python');
    cy.get('td[data-label="Advisory"]').should('have.length', 7);
    cy.get('td[data-label="Package"]')
      .filter(':contains("python")')
      .should('have.length', 7);
  });

  it('render unsupported state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/unsupported.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.contains('Security scan is not supported.');
    cy.contains('Image does not have content the scanner recognizes.');
  });

  it('render failed state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/failed.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.contains('Security scan has failed.');
    cy.contains('The scan could not be completed due to error.');
  });

  it('render queued state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/queued.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.contains('Security scan is currently queued.');
    cy.contains('Refresh page for updates in scan status.');
    cy.contains('Reload');
  });

  // // TODO: Test needs to be implemented
  // it('renders vulnerability description', () => {
  //     cy.visit('/tag/quay/postgres/securityreportqueued?tab=securityreport');
  // });

  it('paginate values', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.contains('1 - 20 of 39').should('exist');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);

    // Change per page
    cy.get('button:contains("1 - 20 of 39")').first().click();
    cy.contains('20 per page').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 20);

    // cycle through the pages
    cy.get('button[aria-label="Go to next page"]').first().click();
    cy.get('td[data-label="Advisory"]').should('have.length', 19);

    // Go to first page
    cy.get('button[aria-label="Go to first page"]').first().click();
    cy.contains('CVE-2019-12900').should('exist');

    // Go to last page
    cy.get('button[aria-label="Go to last page"]').first().click();
    cy.contains('pyup.io-47833 (PVE-2022-47833)').should('exist');

    // Switch per page while while being on a different page
    cy.get('button:contains("21 - 39 of 39")').first().click();
    cy.contains('20 per page').click();
    cy.contains('1 - 20 of 39').should('exist');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
  });

  it('render default desc sorted vulnerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getDescSortedSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('[data-label="Severity"]')
        .get('span:contains("Critical")')
        .should('have.length', 3);
      cy.get('[data-label="Severity"]')
        .get('span:contains("High")')
        .should('have.length', 12);
    });
  });

  it('render asc sorted vulnerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getAscSortedSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport');
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.log('**sort by severity**').wait(1000);
      cy.get('#severity-sort').find('button').click();
    });
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('[data-label="Severity"]')
        .get('span:contains("Unknown")')
        .should('have.length', 1);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Low")')
        .should('have.length', 1);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Medium")')
        .should('have.length', 18);
    });
  });

  it('set vulnerability suppression', () => {
    cy.visit('/repository/user1/hello-world/tag/latest?tab=securityreport');
    cy.get('button').contains('Set Suppressions').click();
    cy.get('[id="vulnerability-suppression-modal"]').should('be.visible');
    cy.get('button').contains('Update').should('be.disabled');
    cy.get('[id="tags-input"]').type('PVE-2022-47833{enter}');
    cy.get('button').contains('Update').should('be.enabled');

    let vulnreport: JSON;
    cy.readFile('cypress/fixtures/security/mixedVulns.json')
      .then((json) => {
        vulnreport = json;
      })
      .as('vulnreport');
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true&suppressions=true',
      (req) =>
        req.reply((res) => {
          const clickFeature = vulnreport.data.Layer.Features.find(
            (feature: any) => feature.Name === 'click',
          );

          // Add the "SuppressedBy" property to the first vulnerability
          _.set(clickFeature, 'Vulnerabilities[0].SuppressedBy', 'manifest');

          // Reply with the modified json
          res.body = vulnreport;

          console.log('Request:', req);
          console.log('Response:', res);
          return res;
        }),
    ).as('getSecurityReportWithSuppression');

    cy.get('button').contains('Update').click();

    cy.get('[id="vulnerability-suppression-modal"]').should('not.exist');
    cy.contains('Quay Security Reporting has detected 38 vulnerabilities');
    cy.contains(
      '3 vulnerabilities are suppressed by the repository and manifest settings',
    );
    cy.contains(
      'Successfully updated vulnerability suppressions for hello-world:latest',
    );
    cy.get('[id="suppressed-checkbox"]').click();
    cy.get('[id="vulnerabilities-search"]').type('PVE-2022-47833');
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.contains('PVE-2022-47833').should('exist');
    });
    cy.get('[data-testid="vulnerability-table"]')
      .find('tbody')
      .first()
      .find('tr')
      .first()
      .find('td')
      .first()
      .find('button')
      .click();
    cy.get('[data-testid="vulnerability-table"]')
      .find('tbody')
      .first()
      .find('tr')
      .contains('This vulnerability is suppressed at the manifest level')
      .should('exist');
  });

  it('Should not be visible without FEATURE_SECURITY_VULNERABILITY_SUPPRESSION', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['SECURITY_VULNERABILITY_SUPPRESSION'] = false;
        return res;
      }),
    ).as('getConfigNoVulnSuppression');
    cy.visit('/repository/user1/hello-world/tag/latest?tab=securityreport');
    cy.get('button').contains('Set Suppressions').should('not.exist');
  });
});
