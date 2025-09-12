/// <reference types="cypress" />

import {formatDate} from '../../src/libs/utils';

describe('Tag Details Page', () => {
  before(() => {
    cy.exec('npm run quay:seed');
  });

  beforeEach(() => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true',
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
    cy.contains('Quay Security Reporting has detected 41 vulnerabilities');
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

  it('switch to security report tab via vulnerabilities field', () => {
    cy.visit('/repository/user1/hello-world/tag/latest');
    cy.contains('12 High').click();
    cy.url().should(
      'include',
      '/repository/user1/hello-world/tag/latest?tab=securityreport',
    );
    cy.contains('Quay Security Reporting has detected 41 vulnerabilities');
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
