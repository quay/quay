/// <reference types="cypress" />

import {formatDate} from '../../src/libs/utils';
import _ from 'lodash';

describe('Tag Details Page', () => {
  before(() => {
    cy.exec('npm run quay:seed');
  });

  beforeEach(() => {
    cy.intercept(
      'GET',
      'http://localhost:8080/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true&suppressions=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('renders details', () => {
    cy.visit('/repository/user1/hello-world/tag/latest');
    cy.get('[data-testid="name"]').contains('latest').should('exist');
    cy.get('[data-testid="creation"]')
      .contains(formatDate('Thu, 27 Jul 2023 17:31:10 -0000'))
      .should('exist');
    cy.get('[data-testid="repository"]')
      .contains('hello-world')
      .should('exist');
    cy.get('[data-testid="modified"]')
      .contains(formatDate('Thu, 27 Jul 2023 17:31:10 -0000'))
      .should('exist');
    cy.get('[data-testid="digest-clipboardcopy"]')
      .contains(
        'sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
      )
      .should('exist');
    cy.get('[data-testid="size"]').contains('2.51 kB').should('exist');
    cy.get('[data-testid="vulnerabilities"]')
      .contains('12 High')
      .should('exist');
    cy.get('[data-testid="vulnerabilities"]')
      .contains('2 Suppressed')
      .should('exist');
    cy.get('[data-testid="labels"]')
      .contains('version = 1.0.0')
      .should('exist');
    cy.get('[data-testid="labels"]')
      .contains('vendor = Redhat')
      .should('exist');
    cy.contains('Fetch Tag').should('exist');
    cy.get('[data-testid="copy-pull-commands"]').within(() => {
      cy.contains('Podman Pull (by tag)').should('exist');
      cy.get('input')
        .eq(0)
        .should(
          'have.value',
          'podman pull localhost:8080/user1/hello-world:latest',
        );
      cy.contains('Docker Pull (by tag)').should('exist');
      cy.get('input')
        .eq(1)
        .should(
          'have.value',
          'docker pull localhost:8080/user1/hello-world:latest',
        );
      cy.contains('Podman Pull (by digest)').should('exist');
      cy.get('input')
        .eq(2)
        .should(
          'have.value',
          'podman pull localhost:8080/user1/hello-world@sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
        );
      cy.contains('Docker Pull (by digest)').should('exist');
      cy.get('input')
        .eq(3)
        .should(
          'have.value',
          'docker pull localhost:8080/user1/hello-world@sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
        );
    });
  });

  it('switch to security report tab', () => {
    cy.visit('/repository/user1/hello-world/tag/latest');
    cy.get('button').contains('Security Report').click();
    cy.url().should(
      'include',
      '/repository/user1/hello-world/tag/latest?tab=securityreport',
    );
    cy.contains('Quay Security Reporting has detected 39 vulnerabilities');
    cy.contains(
      '2 vulnerabilities are suppressed by the repository and manifest settings',
    );
    cy.get('[id="toolbar-pagination"]').contains('39').should('exist');
    cy.get('[id="suppressed-checkbox"]').click();
    cy.get('[id="toolbar-pagination"]').contains('41').should('exist');
  });

  it('switch to packages tab', () => {
    cy.visit('/repository/user1/hello-world/tag/latest');
    cy.get('button').contains('Packages').click();
    cy.url().should(
      'include',
      '/repository/user1/hello-world/tag/latest?tab=packages',
    );
    cy.contains('Quay Security Reporting has recognized 49 packages');
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

  it('switch to security report tab via vulnerabilities field', () => {
    cy.visit('/repository/user1/hello-world/tag/latest');
    cy.contains('12 High').click();
    cy.url().should(
      'include',
      '/repository/user1/hello-world/tag/latest?tab=securityreport',
    );
    cy.contains('Quay Security Reporting has detected 39 vulnerabilities');
  });

  it('switch between architectures', () => {
    cy.visit(
      '/repository/user1/hello-world/tag/manifestlist?digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
    );
    cy.get('[data-testid="name"]').contains('manifestlist').should('exist');
    cy.get('[data-testid="digest-clipboardcopy"]')
      .contains(
        'sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
      )
      .should('exist');
    cy.contains('Architecture').should('exist');
    cy.contains('linux on amd64').should('exist');
    cy.contains('linux on amd64').click();
    cy.contains('linux on arm64').click();
    cy.get('[data-testid="digest-clipboardcopy"]')
      .contains(
        'sha256:432f982638b3aefab73cc58ab28f5c16e96fdb504e8c134fc58dff4bae8bf338',
      )
      .should('exist');
  });
});
