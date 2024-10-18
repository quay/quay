/// <reference types="cypress" />

import moment from 'moment';
import {formatDate} from '../../src/libs/utils';

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
    latestRow.first().within(() => {
      cy.get(`[data-label="Tag"]`).should('have.text', 'latest');
      cy.get(`[data-label="Security"]`).should('have.text', '3 Critical');
      cy.get(`[data-label="Size"]`).should('have.text', '2.48 kB');
      cy.get(`[data-label="Last Modified"]`).should(
        'have.text',
        formatDate('Thu, 27 Jul 2023 17:31:10 -0000'),
      );
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
      cy.get(`[data-label="Digest"]`).should(
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
    manifestListRow.first().within(() => {
      // Assert values for top level row
      cy.get(`[data-label="Tag"]`).should('have.text', 'manifestlist');
      cy.get(`[data-label="Security"]`).should(
        'have.text',
        'See Child Manifests',
      );
      cy.get(`[data-label="Size"]`).should('have.text', '2.51 kB ~ 4.12 kB');
      cy.get(`[data-label="Last Modified"]`).should(
        'have.text',
        formatDate('Thu, 04 Nov 2022 19:15:15 -0000'),
      );
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
      cy.get(`[data-label="Digest"]`).should(
        'have.text',
        'sha256:7693efac53eb',
      );

      // Expand second row
      cy.get('tr').eq(1).should('not.be.visible');
      cy.get('tr').eq(2).should('not.be.visible');
      cy.get('button').first().click();
      cy.get('tr').eq(1).should('not.have.attr', 'hidden');
      cy.get('tr').eq(2).should('not.have.attr', 'hidden');

      // Assert values for first subrow
      cy.get('tr')
        .eq(1)
        .first()
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
        .first()
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
    cy.get('tbody:contains("latest")')
      .first()
      .within(() => cy.get('input').click());
    cy.contains('Actions').click();
    cy.contains('Remove').click();
    cy.contains('Delete the following tag(s)?').should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]')
      .first()
      .within(() => cy.get('button:contains("Delete")').click());
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
    cy.get('tbody:contains("latest")')
      .first()
      .within(() => cy.get('input').click());
    cy.contains('Actions').click();
    cy.contains('Permanently delete').click();
    cy.contains('Permanently delete the following tag(s)?').should('exist');
    cy.contains(
      'Tags deleted cannot be restored within the time machine window and will be immediately eligible for garbage collection.',
    ).should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]')
      .first()
      .within(() => cy.get('button:contains("Delete")').click());
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
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Remove').click();
    cy.contains('Delete the following tag(s)?').should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]')
      .first()
      .within(() => cy.get('button:contains("Delete")').click());
    cy.contains('Deleted tag latest successfully').should('exist');
  });

  it('force deletes tag through row', () => {
    cy.intercept(
      'POST',
      '/api/v1/repository/user1/hello-world/tag/latest/expire',
    ).as('deleteTag');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Permanently delete').click();
    cy.contains('Permanently delete the following tag(s)?').should('exist');
    cy.contains(
      'Tags deleted cannot be restored within the time machine window and will be immediately eligible for garbage collection.',
    ).should('exist');
    cy.contains('Cancel').should('exist');
    cy.get('button').contains('Delete').should('exist');
    cy.get('[id="tag-deletion-modal"]')
      .first()
      .within(() => cy.get('button:contains("Delete")').click());
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
    cy.get('[id="tag-deletion-modal"]')
      .first()
      .within(() => {
        cy.contains('latest').should('exist');
        cy.contains('manifestlist').should('exist');
        cy.get('button').contains('Delete').click();
      });
    cy.contains('latest').should('not.exist');
    cy.contains('manifestlist').should('not.exist');
  });

  it('renders pull popover', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('tbody:contains("latest")')
      .first()
      .within(() => cy.get('td[data-label="Pull"]').trigger('mouseover'));
    cy.get('[data-testid="pull-popover"]')
      .first()
      .within(() => {
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
    cy.get('[data-testid="tag-details"]')
      .first()
      .within(() => {
        cy.contains('latest').should('exist');
        cy.contains(
          'sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
        ).should('exist');
      });
  });

  it('clicking platform name goes to tag details page', () => {
    cy.visit('/repository/user1/hello-world');
    const manifestListRow = cy.get('tbody:contains("manifestlist")').first();
    manifestListRow.first().within(() => {
      cy.get('button').first().click();
      cy.get('a').contains('linux on amd64').click();
    });
    cy.url().should(
      'include',
      '/repository/user1/hello-world/tag/manifestlist?digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4',
    );
    cy.contains('linux on amd64').should('exist');
    cy.get('[data-testid="tag-details"]')
      .first()
      .within(() => {
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
    manifestListRow.first().within(() => {
      cy.get('button').first().click();
      cy.contains('3 Critical').click();
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

  it('search by name via regex', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('[id="filter-input-advanced-search"]').should('not.exist');
    cy.get('[aria-label="Open advanced search"]').click();
    cy.get('[id="filter-input-advanced-search"]').should('be.visible');
    cy.get('[id="filter-input-regex-checker"]').click();
    cy.get('#tagslist-search-input').type('test$');
    cy.contains('latest').should('exist');
    cy.contains('manifestlist').should('not.exist');
    cy.get('[aria-label="Reset search"]').click();
    cy.get('#tagslist-search-input').type('^manifest');
    cy.contains('latest').should('not.exist');
    cy.contains('manifestlist').should('exist');
  });

  it('search by manifest', () => {
    cy.visit('/repository/user1/hello-world');
    cy.get('#toolbar-dropdown-filter').click();
    cy.get('span').contains('Digest').click();
    cy.get('#tagslist-search-input').type('f54a58bc1aac');
    cy.contains('latest').should('exist');
    cy.contains('manifestlist').should('not.exist');
  });

  // FIXME: nested repositories should be fixed by https://issues.redhat.com/browse/PROJQUAY-5446
  it.skip('renders nested repositories', () => {
    cy.visit('/repository/user1/nested/repo');
    cy.get('[data-testid="repo-title"]')
      .first()
      .within(() => cy.contains('nested/repo').should('exist'));
    cy.contains('There are no viewable tags for this repository').should(
      'exist',
    );
  });

  it('does not render tag actions for non-writable repositories', () => {
    cy.visit('/repository/user2org1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').should('not.exist');
    });
  });

  it('adds tag', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Add new tag').click();
    cy.contains('Add tag to manifest sha256:f54a58bc1aa').should('exist');
    cy.get('input[placeholder="New tag name"]').type('newtag');
    cy.contains('Create tag').click();
    cy.contains('Successfully created tag newtag').should('exist');
    const newtagRow = cy.get('tbody:contains("newtag")');
    newtagRow.first().within(() => {
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
    latestRow.first().within(() => {
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
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#readonly-labels')
      .first()
      .within(() => {
        cy.contains('No labels found').should('exist');
      });
    cy.get('#mutable-labels')
      .first()
      .within(() => {
        cy.contains('version=1.0.0').should('exist');
        cy.contains('vendor=Redhat').should('exist');
      });
  });

  it('creates labels', () => {
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#mutable-labels').within(() => {
      cy.contains('version=1.0.0').should('exist');
      cy.contains('vendor=Redhat').should('exist');
    });
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
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#mutable-labels').within(() => {
      cy.get('button').should('exist');
      cy.get('button').then((buttons) => {
        for (let i = 0; i < buttons.length; i++) {
          cy.get('button').first().click();
        }
      });
    });
    cy.contains('Save Labels').click();
    cy.contains('Deleted labels successfully').should('exist');
  });

  it('alert on failure to create label', () => {
    cy.intercept('POST', '**/labels', {statusCode: 500}).as('getServerFailure');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
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
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Edit labels').click();
    cy.get('#mutable-labels').within(() => {
      cy.get('button').should('exist');
      cy.get('button').then((buttons) => {
        for (let i = 0; i < buttons.length; i++) {
          cy.get('button').first().click();
        }
      });
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
    cy.get(`[data-label="Expires"]`)
      .first()
      .within(() => {
        cy.contains('a month');
      });
  });

  it('changes expiration through kebab', () => {
    const formattedDate = new Date();
    const currentDateGB = formattedDate.toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    // for some reason the date picker is always using UK date formats for the aria labels
    const currentDateLong = formattedDate.toLocaleDateString(
      navigator.language,
      {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      },
    );
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    nextMonth.setHours(1);
    nextMonth.setMinutes(0);
    const formattedTime = nextMonth.toLocaleTimeString(navigator.language, {
      hour: 'numeric',
      minute: '2-digit',
    });

    nextMonth.setHours(2);
    nextMonth.setMinutes(3);
    const formattedTime2 = nextMonth.toLocaleTimeString(navigator.language, {
      hour: 'numeric',
      minute: '2-digit',
    });
    const oneMonthFormatLong = nextMonth.toLocaleString(navigator.language, {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timeStyle: 'short',
      dateStyle: 'medium',
    });

    // Start
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Change expiration').click();
    cy.get('#edit-expiration-tags')
      .first()
      .within(() => {
        cy.contains('latest').should('exist');
      });

    // Ensure current date can be chosen
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get(`[aria-label="${currentDateGB}"]`).click();
    cy.get('input[aria-label="Date picker"]').should(
      'have.value',
      currentDateLong,
    );

    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    cy.get(`[aria-label="${sameDateNextMonthGB}"]`).click();

    cy.get('#expiration-time-picker').click();
    cy.contains(formattedTime.replace(/ AM| PM/, ''))
      .scrollIntoView()
      .click();
    cy.get('#expiration-time-picker-input').clear();
    cy.get('#expiration-time-picker-input').type(
      formattedTime2.replace(/ AM| PM/, ''),
    );

    // remove AM/PM suffixes because the TimePicker adds those automatically
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.first().within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', ' a month');
    });

    cy.contains(
      `Successfully set expiration for tag latest to ${oneMonthFormatLong}`,
    ).should('exist');

    // Reset back to Never
    latestRow.first().within(() => {
      cy.get('#tag-actions-kebab').click();
    });
    cy.contains('Change expiration').click();
    cy.contains('Clear').click();
    cy.contains('Change Expiration').click();

    const latestRowUpdatedNever = cy.get('tbody:contains("latest")');
    latestRowUpdatedNever.first().within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
    });
    cy.contains(`Successfully set expiration for tag latest to never`).should(
      'exist',
    );
  });

  it('changes expiration through tag row', () => {
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    nextMonth.setHours(1);
    nextMonth.setMinutes(0);
    const formattedTime = nextMonth.toLocaleTimeString(navigator.language, {
      hour: 'numeric',
      minute: '2-digit',
    });
    const oneMonthFormatLong = nextMonth.toLocaleString(navigator.language, {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timeStyle: 'short',
      dateStyle: 'medium',
    });

    // Start
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.contains('Never').click();
    });
    cy.get('#edit-expiration-tags')
      .first()
      .within(() => {
        cy.contains('latest').should('exist');
      });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    cy.get(`[aria-label="${sameDateNextMonthGB}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains(formattedTime).click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.first().within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', ' a month');
    });
    cy.contains(
      `Successfully set expiration for tag latest to ${oneMonthFormatLong}`,
    ).should('exist');
  });

  it('changes multiple tag expirations', () => {
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    nextMonth.setHours(1);
    nextMonth.setMinutes(0);
    const formattedTime = nextMonth.toLocaleTimeString(navigator.language, {
      hour: 'numeric',
      minute: '2-digit',
    });
    const oneMonthFormatLong = nextMonth.toLocaleString(navigator.language, {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timeStyle: 'short',
      dateStyle: 'medium',
    });

    // Start
    cy.visit('/repository/user1/hello-world');
    cy.get('#toolbar-dropdown-checkbox').click();
    cy.get('button').contains('Select page (2)').click();
    cy.contains('Actions').click();
    cy.contains('Set expiration').click();
    cy.get('#edit-expiration-tags')
      .first()
      .within(() => {
        cy.contains('latest').should('exist');
        cy.contains('manifestlist').should('exist');
      });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    cy.get(`[aria-label="${sameDateNextMonthGB}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains(formattedTime).click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.first().within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', ' a month');
    });
    cy.contains(
      `Successfully updated tag expirations to ${oneMonthFormatLong}`,
    ).should('exist');
  });

  it('alerts on failure to change expiration', () => {
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const sameDateNextMonthGB = nextMonth.toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    nextMonth.setHours(1);
    nextMonth.setMinutes(0);
    const formattedTime = nextMonth.toLocaleTimeString(navigator.language, {
      hour: 'numeric',
      minute: '2-digit',
    });

    // Start
    cy.intercept('PUT', '/api/v1/repository/user1/hello-world/tag/latest', {
      statusCode: 500,
    }).as('getServerFailure');
    cy.visit('/repository/user1/hello-world');
    const latestRow = cy.get('tbody:contains("latest")');
    latestRow.first().within(() => {
      cy.contains('Never').click();
    });
    cy.get('[aria-label="Toggle date picker"]').click();
    cy.get('button[aria-label="Next month"]').click();
    cy.get(`[aria-label="${sameDateNextMonthGB}"]`).click();
    cy.get('#expiration-time-picker').click();
    cy.contains(formattedTime).click();
    cy.contains('Change Expiration').click();
    const latestRowUpdated = cy.get('tbody:contains("latest")');
    latestRowUpdated.first().within(() => {
      cy.get(`[data-label="Expires"]`).should('have.text', 'Never');
    });
    cy.contains(`Could not set expiration for tag latest`).should('exist');
  });
});

describe('Tag history Tab', () => {
  const tagHistoryRows = [
    {
      change:
        'latest was reverted to sha256f54a58bc1aac5e from sha2567e9b6e7ba2842c',
      date: 'Thu, 27 Jul 2023 17:31:10 -0000',
      revert: 'Restore to sha2567e9b6e7ba2842c',
    },
    {
      change:
        'latest was moved to sha2567e9b6e7ba2842c from sha256f54a58bc1aac5e',
      date: 'Thu, 27 Jul 2023 17:30:10 -0000',
      revert: 'Revert to sha256f54a58bc1aac5e',
    },
    {
      change: 'latest was recreated pointing to sha256f54a58bc1aac5e',
      date: 'Thu, 27 Jul 2023 17:30:10 -0000',
    },
    {
      change: 'latest was deleted',
      date: 'Thu, 27 Jul 2023 17:30:10 -0000',
      revert: 'Restore to sha256f54a58bc1aac5e',
    },
    {
      change: 'manifestlist was created pointing to sha2567693efac53eb85',
      date: 'Fri, 4 Nov 2022 19:15:10 -0000',
    },
    {
      change: 'latest was created pointing to sha256f54a58bc1aac5e',
      date: 'Fri, 4 Nov 2022 19:13:10 -0000',
    },
  ];

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('renders history list', () => {
    cy.visit('/repository/user1/hello-world');
    cy.contains('Tag history').click();
    cy.get('#tag-history-table > tr').each(($e, index, $list) => {
      cy.wrap($e).within(() => {
        const expectedValues = tagHistoryRows[index];
        cy.get(`[data-label="tag-change"]`).should(
          'have.text',
          expectedValues.change,
        );
        cy.get(`[data-label="date-modified"]`).should(
          'have.text',
          formatDate(expectedValues.date),
        );
        if (expectedValues.revert) {
          cy.get(`[data-label="restore-tag"]`).should(
            'have.text',
            expectedValues.revert,
          );
        }
      });
    });
  });

  it('search by name', () => {
    cy.visit('/repository/user1/hello-world');
    cy.contains('Tag history').click();
    cy.get('input[placeholder="Search by tag name..."').type('manifestlist');
    cy.get('#tag-history-table > tr').each(($e, index, $list) => {
      cy.wrap($e).within(() => {
        cy.get(`[data-label="tag-change"]`).should(
          'contain.text',
          'manifestlist',
        );
      });
    });
  });

  it('show future entries', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/tag/**',
      (req) => {
        // Add expiration to show up as future entry
        req.continue((res) => {
          const expiration = moment().add(2, 'weeks');
          res.body.tags[0].end_ts = expiration.unix();
          res.body.tags[0].expiration = expiration.toISOString();
        });
      },
    );
    cy.visit('/repository/user1/hello-world');
    cy.contains('Tag history').click();
    cy.contains('latest will expire').should('not.exist');
    cy.get('#show-future-checkbox').click();
    cy.contains('latest will expire').should('exist');
  });

  it('filter by date range', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/tag/**',
      (req) => {
        req.continue((res) => {
          // Add expiration to show up as future entry
          const expiration = moment().add(2, 'weeks');
          res.body.tags[0].end_ts = expiration.unix();
          res.body.tags[0].expiration = expiration.toISOString();
        });
      },
    );
    cy.visit('/repository/user1/hello-world');
    cy.contains('Tag history').click();
    cy.get('#show-future-checkbox').click();
    cy.get('#start-time-picker').within(() => {
      cy.get('input[aria-label="Date picker"]').type('2023-07-26');
    });
    cy.get('#tag-history-table > tr').each(($e, index, $list) => {
      cy.wrap($e).within(() => {
        cy.get(`[data-label="date-modified"]`).then(($el) => {
          const dateMoment = moment($el.text());
          expect(dateMoment.isAfter('July 26, 2023'));
        });
      });
    });
    cy.get('#end-time-picker').within(() => {
      cy.get('input[aria-label="Date picker"]').type('2023-07-28');
    });
    cy.get('#tag-history-table > tr').each(($e, index, $list) => {
      cy.wrap($e).within(() => {
        cy.get(`[data-label="date-modified"]`).then(($el) => {
          const dateMoment = moment($el.text());
          expect(dateMoment.isBefore('July 26, 2023'));
        });
      });
    });
  });

  it('revert tag', () => {
    cy.visit('/repository/user1/hello-world');
    cy.contains('Tag history').click();
    cy.contains('Restore to sha2567e9b6e7ba2842c').click();
    cy.contains('Restore Tag').should('exist');
    cy.contains('This will change the image to which the tag points.').should(
      'exist',
    );
    cy.contains(
      'Are you sure you want to restore tag latest to image sha2567e9b6e7ba2842c?',
    ).should('exist');
    cy.contains('Restore tag').click();
    cy.contains(
      'Restored tag latest to digest sha256:7e9b6e7 successfully',
    ).should('exist');
  });

  it('permanently delete tag', () => {
    cy.intercept(
      'POST',
      '/api/v1/repository/user1/hello-world/tag/testdelete/expire',
    ).as('deleteTag');
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/tag/**',
      (req) => {
        req.continue((res) => {
          const start = moment().subtract(5, 'days');
          const end = moment().subtract(3, 'days');
          res.body.tags.unshift({
            name: 'testdelete',
            reversion: false,
            start_ts: start.unix(),
            end_ts: end.unix(),
            manifest_digest:
              'sha256:12345e7ba2842c91cf49f3e214d04a7a496f8214356f41d81a6e6dcad11f11e3',
            is_manifest_list: false,
            size: 2457,
            last_modified: end.toISOString(),
            expiration: end.toISOString(),
          });
        });
      },
    );
    cy.visit('/repository/user1/hello-world');
    cy.contains('Tag history').click();
    cy.contains('Delete testdelete sha25612345e7ba2842c ').click(10, 10);
    cy.contains('Permanently Delete Tag').should('exist');
    cy.contains(
      'The tag deleted cannot be restored within the time machine window and references to the tag will be removed from tag history. Any alive tags with the same name and digest will not be effected.',
    ).should('exist');
    cy.contains(
      'Are you sure you want to permanently delete tag testdelete @ sha25612345e7ba2842c?',
    ).should('exist');
    cy.contains('Permanently delete tag').click();
    cy.wait('@deleteTag', {timeout: 20000}).should((xhr) => {
      expect(xhr.request.body.include_submanifests).eq(true);
      expect(xhr.request.body.is_alive).eq(false);
      expect(xhr.request.body.manifest_digest).eq(
        'sha256:12345e7ba2842c91cf49f3e214d04a7a496f8214356f41d81a6e6dcad11f11e3',
      );
    });
  });

  it('cannot revert or delete if user has no write permissions', () => {
    cy.visit('/repository/user2org1/hello-world?tab=history');
    cy.contains('latest was created pointing to sha256f54a58bc1aac5e').should(
      'exist',
    );
    cy.contains('Revert').should('not.exist');
    cy.contains('Permanently delete').should('not.exist');
  });
});
