/// <reference types="cypress" />

import {formatDate} from '../../src/libs/utils';

describe('Repository Details Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('renders tag', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get(`[data-label="Name"]`).should('have.text', 'latest');
      cy.get(`[data-label="Security"]`).should('have.text', '3 Critical');
      cy.get(`[data-label="Size"]`).should('have.text', '2.48 kB');
      cy.get(`[data-label="Last Modified"]`).should(
        'have.text',
        formatDate('Thu, 04 Nov 2022 19:13:59 -0000'),
      );
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
      cy.get(`[data-label="Manifest"]`).should(
        'have.text',
        'sha256:f54a58bc1aac',
      );
    });
  });

  it('renders manifest list tag', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world');

    const manifestListRow = cy.get('tbody:contains("manifestlist")');
    manifestListRow.within(() => {
      // Assert values for top level row
      cy.get(`[data-label="Name"]`).should('have.text', 'manifestlist');
      cy.get(`[data-label="Security"]`).should(
        'have.text',
        'See Child Manifests',
      );
      cy.get(`[data-label="Size"]`).should('have.text', 'Unknown');
      cy.get(`[data-label="Last Modified"]`).should(
        'have.text',
        formatDate('Thu, 04 Nov 2022 19:15:15 -0000'),
      );
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
      cy.get(`[data-label="Manifest"]`).should(
        'have.text',
        'sha256:7693efac53eb',
      );

      // Expand second row
      cy.get('tr').eq(1).should('not.be.visible');
      cy.get('tr').eq(2).should('not.be.visible');
      cy.get('button').first().click();
      cy.get('tr').eq(1).should('be.visible');
      cy.get('tr').eq(2).should('be.visible');

      // Assert values for first subrow
      cy.get('tr')
        .eq(1)
        .within(() => {
          cy.get(`[data-label="platform"]`).should(
            'have.text',
            'linux on amd64',
          );
          cy.get(`[data-label="security"]`).should('have.text', '3 Critical');
          cy.get(`[data-label="size"]`).should('have.text', '2.51 kB');
          cy.get(`[data-label="digest"]`).should(
            'have.text',
            'sha256:f54a58bc1aac',
          );
        });

      // Assert values for second subrow
      cy.get('tr')
        .eq(2)
        .within(() => {
          cy.get(`[data-label="platform"]`).should('have.text', 'linux on arm');
          cy.get(`[data-label="security"]`).should('have.text', 'Queued');
          cy.get(`[data-label="size"]`).should('have.text', '3.72 kB');
          cy.get(`[data-label="digest"]`).should(
            'have.text',
            'sha256:7b8b7289d053',
          );
        });
    });
  });

  it('deletes tag', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('tbody:contains("latest")').within(() => cy.get('input').click());
    cy.contains('Actions').click();
    cy.contains('Delete').click();
    cy.contains('Delete the following tag?').should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]').within(() =>
      cy.get('button:contains("Delete")').click(),
    );
    cy.contains('latest').should('not.exist');
  });

  it('bulk deletes tags', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('#toolbar-dropdown-checkbox').click();
    cy.get('button').contains('Select page (2)').click();
    cy.contains('Actions').click();
    cy.contains('Delete').click();
    cy.contains('Delete the following tags?').should('exist');
    cy.contains('Note: This operation can take several minutes.').should(
      'exist',
    );
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]').within(() => {
      cy.contains('latest').should('exist');
      cy.contains('manifestlist').should('exist');
      cy.get('button').contains('Delete').click();
    });
    cy.contains('latest').should('not.exist');
    cy.contains('manifestlist').should('not.exist');
  });

  it('renders pull popover', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('tbody:contains("latest")').within(() =>
      cy.get('svg').trigger('mouseover'),
    );
    cy.get('[data-testid="pull-popover"]').within(() => {
      cy.contains('Fetch Tag').should('exist');
      cy.contains('Podman Pull (By Tag)').should('exist');
      cy.get('input')
        .first()
        .should(
          'have.value',
          'podman pull localhost:8080/user1/hello-world:latest',
        );
      cy.contains('Podman Pull (By Digest)').should('exist');
      cy.get('input')
        .eq(1)
        .should(
          'have.value',
          'podman pull localhost:8080/user1/hello-world@sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
        );
      cy.contains('Docker Pull (By Tag)').should('exist');
      cy.get('input')
        .eq(2)
        .should(
          'have.value',
          'docker pull localhost:8080/user1/hello-world:latest',
        );
      cy.contains('Docker Pull (By Digest)').should('exist');
      cy.get('input')
        .eq(3)
        .should(
          'have.value',
          'docker pull localhost:8080/user1/hello-world@sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
        );
    });
  });

  it('clicking tag name goes to tag details page', () => {
    cy.visit('/repository/user1/hello-world');
    cy.contains('latest').click();
    cy.url().should('include', '/tag/user1/hello-world/latest');
    cy.get('[data-testid="tag-details"]').within(() => {
      cy.contains('latest').should('exist');
      cy.contains(
        'sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
      ).should('exist');
    });
  });

  it('clicking platform name goes to tag details page', () => {
    cy.visit('/repository/user1/hello-world');
    const manifestListRow = cy.get('tbody:contains("manifestlist")').first();
    manifestListRow.within(() => {
      cy.get('button').first().click();
      cy.get('a').contains('linux on amd64').click();
    });
    cy.url().should(
      'include',
      '/tag/user1/hello-world/manifestlist?digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
    );
    cy.contains('linux on amd64').should('exist');
    cy.get('[data-testid="tag-details"]').within(() => {
      cy.contains('manifestlist').should('exist');
      cy.contains(
        'sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
      ).should('exist');
    });
  });

  it('clicking tag security data goes to security report page', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world');
    cy.get('tr:contains("latest")').contains('3 Critical').click();
    cy.url().should(
      'include',
      '/tag/user1/hello-world/latest?tab=securityreport&digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
    );
    cy.contains(
      'Quay Security Reporting has detected 41 vulnerabilities',
    ).should('exist');
    cy.contains('latest').should('exist');
  });

  it('clicking platform security data goes to security report page', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world');
    const manifestListRow = cy.get('tbody:contains("manifestlist")');
    manifestListRow.within(() => {
      cy.get('button').first().click();
      cy.get('a').contains('3 Critical').click();
    });
    cy.url().should(
      'include',
      '/tag/user1/hello-world/manifestlist?tab=securityreport&digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
    );
    cy.contains('linux on amd64').should('exist');
    cy.contains(
      'Quay Security Reporting has detected 41 vulnerabilities',
    ).should('exist');
  });

  it('search by name', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('#tagslist-search-input').type('test');
    cy.contains('latest').should('exist');
    cy.contains('manifestlist').should('not.exist');
  });

  it('search by manifest', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('#toolbar-dropdown-filter').click();
    cy.get('a').contains('Manifest').click();
    cy.get('#tagslist-search-input').type('f54a58bc1aac');
    cy.contains('latest').should('exist');
    cy.contains('manifestlist').should('not.exist');
  });

  it('renders nested repositories', () => {
    cy.visit('/repository/user1/nested/repo');
    cy.get('[data-testid="repo-title"]').within(() =>
      cy.contains('nested/repo').should('exist'),
    );
    cy.contains('There are no viewable tags for this repository').should(
      'exist',
    );
  });
});
