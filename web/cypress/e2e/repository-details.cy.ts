/// <reference types="cypress" />

import {formatDate} from '../../src/libs/utils';
import moment from 'moment';

describe('Repository Details Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
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
    cy.intercept(
      'DELETE',
      '/api/v1/repository/user1/hello-world/tag/latest',
    ).as('deleteTag');
    cy.visit('/repository/user1/hello-world');
    cy.get('tbody:contains("latest")').within(() => cy.get('input').click());
    cy.contains('Actions').click();
    cy.contains('Remove').click();
    cy.contains('Delete the following tag(s)?').should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]').within(() =>
      cy.get('button:contains("Delete")').click(),
    );
    cy.wait('@deleteTag', {timeout: 20000})
      .its('request.url')
      .should('contain', '/api/v1/repository/user1/hello-world/tag/latest');
  });

  it('force deletes tag', () => {
    cy.intercept(
      'POST',
      '/api/v1/repository/user1/hello-world/tag/latest/expire',
    ).as('deleteTag');
    cy.visit('/repository/user1/hello-world');
    cy.get('tbody:contains("latest")').within(() => cy.get('input').click());
    cy.contains('Actions').click();
    cy.contains('Permanently Delete').click();
    cy.contains('Permanently delete the following tag(s)?').should('exist');
    cy.contains(
      'Tags deleted cannot be restored within the time machine window and will be immediately eligible for garbage collection.',
    ).should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]').within(() =>
      cy.get('button:contains("Delete")').click(),
    );
    cy.wait('@deleteTag', {timeout: 20000})
      .its('request.url')
      .should(
        'contain',
        '/api/v1/repository/user1/hello-world/tag/latest/expire',
      );
  });

  it('deletes tag through row', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Remove').click();
    cy.contains('Delete the following tag(s)?').should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]').within(() =>
      cy.get('button:contains("Delete")').click(),
    );
    cy.contains('Deleted tag latest successfully').should('exist');
  });

  it('force deletes tag through row', () => {
    cy.intercept(
      'POST',
      '/api/v1/repository/user1/hello-world/tag/latest/expire',
    ).as('deleteTag');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Permanently Delete').click();
    cy.contains('Permanently delete the following tag(s)?').should('exist');
    cy.contains(
      'Tags deleted cannot be restored within the time machine window and will be immediately eligible for garbage collection.',
    ).should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]').within(() =>
      cy.get('button:contains("Delete")').click(),
    );
    cy.wait('@deleteTag', {timeout: 20000})
      .its('request.url')
      .should(
        'contain',
        '/api/v1/repository/user1/hello-world/tag/latest/expire',
      );
  });

  it('bulk deletes tags', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('#toolbar-dropdown-checkbox').click();
    cy.get('button').contains('Select page (2)').click();
    cy.contains('Actions').click();
    cy.contains('Remove').click();
    cy.contains('Delete the following tag(s)?').should('exist');
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
      cy.get('td[data-label="Pull"]').trigger('mouseover'),
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
    cy.url().should('include', '/repository/user1/hello-world/tag/latest');
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
      '/repository/user1/hello-world/tag/manifestlist?digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
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
      '/repository/user1/hello-world/tag/latest?tab=securityreport&digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
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
      '/repository/user1/hello-world/tag/manifestlist?tab=securityreport&digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
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

  // FIXME: nested repositories should be fixed by https://issues.redhat.com/browse/PROJQUAY-5446
  it.skip('renders nested repositories', () => {
    cy.visit('/repository/user1/nested/repo');
    cy.get('[data-testid="repo-title"]').within(() =>
      cy.contains('nested/repo').should('exist'),
    );
    cy.contains('There are no viewable tags for this repository').should(
      'exist',
    );
  });

  it('does not render tag actions for non-writable repositories', () => {
    cy.visit('/repository/user2org1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').should('not.exist');
    });
  });

  it('adds tag', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Add new tag').click();
    cy.contains('Add tag to manifest sha256:f54a58bc1aa').should('exist');
    cy.get('input[placeholder="New tag name"]').type('newtag');
    cy.contains('Create tag').click();
    cy.contains('Successfully created tag newtag').should('exist');
    const newtagRow = cy.get('tbody:contains("newtag")');
    newtagRow.within(() => {
      cy.contains('newtag').should('exist');
      cy.contains('sha256:f54a58bc1aa').should('exist');
    });
  });

  it('alert on failure to add tag', () => {
    cy.intercept('PUT', '/api/v1/repository/user1/hello-world/tag/newtag', {
      statusCode: 500,
    }).as('getServerFailure');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Add new tag').click();
    cy.contains('Add tag to manifest sha256:f54a58bc1aa').should('exist');
    cy.get('input[placeholder="New tag name"]').type('newtag');
    cy.contains('Create tag').click();
    cy.contains('Could not create tag newtag').should('exist');
    const newtagRow = cy.get('tbody:contains("newtag")').should('not.exist');
  });

  it('view labels', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#readonly-labels').within(() => {
      cy.contains('No labels found').should('exist');
    });
    cy.get('#mutable-labels').within(() => {
      cy.contains('version=1.0.0').should('exist');
      cy.contains('vendor=Redhat').should('exist');
    });
  });

  it('creates labels', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.contains('Add new label').click();
    cy.get('input[placeholder="key=value"]').type('foo=bar');
    cy.contains('Mutable labels').click(); // Simulates clicking outside of input
    cy.contains('Add new label').click();
    cy.get('input[placeholder="key=value"]').type('fizz=buzz');
    cy.contains('Mutable labels').click();
    cy.contains('Save Labels').click();
    cy.contains('Created labels successfully').should('exist');
  });

  it('deletes labels', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#mutable-labels').within(() => {
      cy.get('button').should('exist');
      cy.get('button').click({multiple: true});
    });
    cy.contains('Save Labels').click();
    cy.contains('Deleted labels successfully').should('exist');
  });

  it('alert on failure to create label', () => {
    cy.intercept('POST', '**/labels', {statusCode: 500}).as('getServerFailure');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.contains('Add new label').click();
    cy.get('input[placeholder="key=value"]').type('foo=bar');
    cy.contains('Mutable labels').click(); // Simulates clicking outside of input
    cy.contains('Add new label').click();
    cy.get('input[placeholder="key=value"]').type('fizz=buzz');
    cy.contains('Mutable labels').click();
    cy.contains('Save Labels').click();
    cy.contains('Could not create labels').should('exist');
  });

  it('alert on failure to delete label', () => {
    cy.intercept('DELETE', '**/labels/**', {statusCode: 500}).as(
      'getServerFailure',
    );
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#mutable-labels').within(() => {
      cy.get('button').should('exist');
      cy.get('button').click({multiple: true});
    });
    cy.contains('Save Labels').click();
    cy.contains('Could not delete labels').should('exist');
  });

  it('renders tag with no expiration', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/testorg/testrepo/tag/?limit=100&page=1&onlyActiveTags=true',
      {fixture: 'single-tag.json'},
    ).as('getTag');
    cy.visit('/repository/testorg/testrepo');
    cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
  });

  it('renders tag with expiration within a month', () => {
    cy.fixture('single-tag.json').then((fixture) => {
      fixture.tags[0].expiration = moment(new Date().toString())
        .add(1, 'month')
        .format('ddd, DD MMM YYYY HH:mm:ss ZZ');
      cy.intercept(
        'GET',
        '/api/v1/repository/testorg/testrepo/tag/?limit=100&page=1&onlyActiveTags=true',
        fixture,
      ).as('getTag');
    });
    cy.visit('/repository/testorg/testrepo');
    cy.get(`[data-label="Expires"]`).within(() => {
      cy.contains('a month');
    });
  });

  it('changes expiration through kebab', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Change expiration').click();
    cy.get('#edit-expiration-tags').within(() => {
      cy.contains('latest').should('exist');
    });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    const oneMonth = moment().add(1, 'month').format('D MMMM YYYY');
    cy.get(`[aria-label="${oneMonth}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains('1:00 AM').click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', ' a month');
    });
    const oneMonthFormat = moment().add(1, 'month').format('MMM D, YYYY');
    cy.contains(
      `Successfully set expiration for tag latest to ${oneMonthFormat}, 1:00 AM`,
    ).should('exist');

    // Reset back to Never
    latestRow.within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Change expiration').click();
    cy.get('input[aria-label="Date picker"]').clear();
    cy.contains('Change Expiration').click();

    const latestRowUpdatedNever = cy.get('tbody:contains("latest")');
    latestRowUpdatedNever.within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
    });
    cy.contains(`Successfully set expiration for tag latest to never`).should(
      'exist',
    );
  });

  it('changes expiration through tag row', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.contains('Never').click();
    });
    cy.get('#edit-expiration-tags').within(() => {
      cy.contains('latest').should('exist');
    });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    const oneMonth = moment().add(1, 'month').format('D MMMM YYYY');
    cy.get(`[aria-label="${oneMonth}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains('1:00 AM').click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', ' a month');
    });
    const oneMonthLongFormat = moment().add(1, 'month').format('MMM D, YYYY');
    cy.contains(
      `Successfully set expiration for tag latest to ${oneMonthLongFormat}, 1:00 AM`,
    ).should('exist');
  });

  it('changes multiple tag expirations', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('#toolbar-dropdown-checkbox').click();
    cy.get('button').contains('Select page (2)').click();
    cy.contains('Actions').click();
    cy.contains('Set expiration').click();
    cy.get('#edit-expiration-tags').within(() => {
      cy.contains('latest').should('exist');
      cy.contains('manifestlist').should('exist');
    });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    const oneMonth = moment().add(1, 'month').format('D MMMM YYYY');
    cy.get(`[aria-label="${oneMonth}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains('1:00 AM').click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', ' a month');
    });
    const tomorrowLongFormat = moment().add(1, 'month').format('MMM D, YYYY');
    cy.contains(
      `Successfully updated tag expirations to ${tomorrowLongFormat}, 1:00 AM`,
    ).should('exist');
  });

  it('alerts on failure to change expiration', () => {
    cy.intercept('PUT', '/api/v1/repository/user1/hello-world/tag/latest', {
      statusCode: 500,
    }).as('getServerFailure');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.within(() => {
      cy.contains('Never').click();
    });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    const oneMonth = moment().add(1, 'month').format('D MMMM YYYY');
    cy.get(`[aria-label="${oneMonth}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains('1:00 AM').click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
    });
    const oneMonthLongFormat = moment().add(1, 'month').format('MMM D, YYYY');
    cy.contains(`Could not set expiration for tag latest`).should('exist');
  });
});
