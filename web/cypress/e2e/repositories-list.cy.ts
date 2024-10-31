/// <reference types="cypress" />

import {formatDate} from '../../src/libs/utils';
import {IRepository} from '../../src/resources/RepositoryResource';

describe('Repositories List Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('renders list of all repositories', () => {
    cy.visit('/repository');
    cy.contains('Repositories').should('exist');
    cy.get('[data-testid="repository-list-table"]')
      .children()
      .should('have.length', 20);
    cy.get('#repositorylist-search-input').type('user1');
    cy.get('[data-testid="repository-list-table"]').within(() => {
      cy.contains('user1/hello-world').should('exist');
      cy.contains('user1/nested/repo').should('exist');
    });
    const firstRow = cy.get('tbody').first();
    firstRow.within(() => {
      cy.get(`[data-label="Name"]`).contains('user1/hello-world');
      cy.get(`[data-label="Visibility"]`).contains('private');
      //cy.get(`[data-label="Size"]`).contains('2.42 kB');
      cy.get(`[data-label="Last Modified"]`).contains(
        formatDate('Thu, 27 Jul 2023 17:31:10 -0000'),
      );
    });
  });

  it('renders list of repositories for a single organization', () => {
    cy.visit('/organization/user1');
    cy.get('[data-testid="repo-title"]').within(() => cy.contains('user1'));
    cy.get('[data-testid="repository-list-table"]')
      .children()
      .should('have.length', 2);
    cy.get('[data-testid="repository-list-table"]').within(() => {
      cy.contains('hello-world').should('exist');
      cy.contains('nested/repo').should('exist');
    });
    const firstRow = cy.get('tbody').first();
    firstRow.within(() => {
      cy.get(`[data-label="Name"]`).contains('hello-world');
      cy.get(`[data-label="Visibility"]`).contains('private');
      //cy.get(`[data-label="Size"]`).contains('2.42 kB');
      cy.get(`[data-label="Last Modified"]`).contains(
        formatDate('Thu, 27 Jul 2023 17:31:10 -0000'),
      );
    });
  });

  it('create public repository', () => {
    cy.intercept('/repository').as('getRepositories');
    cy.visit('/repository');
    cy.wait('@getRepositories');
    cy.contains('Create Repository').click();
    cy.contains('Create Repository').should('exist');
    cy.get('[data-testid="selected-namespace-dropdown"]').click();
    cy.get('[data-testid="user-user1"]').click();
    cy.get('input[id="repository-name-input"]').type('new-repo');
    cy.get('input[id="repository-description-input"]').type(
      'This is a new public repository',
    );
    cy.get('[id="create-repository-modal"]').within(() =>
      cy.get('button:contains("Create")').click(),
    );
    cy.get('#repositorylist-search-input').type('user1');
    cy.contains('user1/new-repo').should('exist');
    cy.get('tr:contains("user1/new-repo")').within(() =>
      cy.contains('public').should('exist'),
    );
  });

  it('create private repository', () => {
    cy.visit('/repository');
    cy.contains('Create Repository').click();
    cy.contains('Create Repository').should('exist');
    cy.get('[data-testid="selected-namespace-dropdown"]').click();
    cy.get('[data-testid="user-user1"]').click();
    cy.get('input[id="repository-name-input"]').type('new-repo');
    cy.get('input[id="repository-description-input"]').type(
      'This is a new private repository',
    );
    cy.get('input[id="PRIVATE"]').click();
    cy.get('[id="create-repository-modal"]').within(() =>
      cy.get('button:contains("Create")').click(),
    );
    cy.get('#repositorylist-search-input').type('user1');
    cy.contains('new-repo').should('exist');
    cy.get('tr:contains("new-repo")').within(() =>
      cy.contains('private').should('exist'),
    );
  });

  it('create repository under organization', () => {
    cy.visit('/organization/testorg');
    cy.contains('Create Repository').click();
    cy.contains('Create Repository').should('exist');
    cy.get('button:contains("testorg")').should('exist');
    cy.get('input[id="repository-name-input"]').type('new-repo');
    cy.get('input[id="repository-description-input"]').type(
      'This is a new private repository',
    );
    cy.get('input[id="PRIVATE"]').click();
    cy.get('[id="create-repository-modal"]').within(() =>
      cy.get('button:contains("Create")').click(),
    );
    cy.contains('new-repo').should('exist');
    cy.get('tr:contains("new-repo")').within(() =>
      cy.contains('private').should('exist'),
    );
  });

  it('deletes multiple repositories', () => {
    cy.visit('/organization/user1');
    cy.get('button[id="toolbar-dropdown-checkbox"]').click();
    cy.contains('Select all (2)').click();
    cy.contains('Actions').click();
    cy.contains('Delete').click();
    cy.contains('Permanently delete repositories?');
    cy.contains(
      'This action deletes all repositories and cannot be recovered.',
    );
    cy.contains('Confirm deletion by typing "confirm" below:');
    cy.get('input[id="delete-confirmation-input"]').type('confirm');
    cy.get('[id="bulk-delete-modal"]')
      .within(() => cy.get('button:contains("Delete")').click())
      .then(() => {
        cy.contains('There are no viewable repositories').should('exist');
        cy.contains(
          'Either no repositories exist yet or you may not have permission to view any. If you have permission, try creating a new repository.',
        ).should('exist');
        cy.contains('Create Repository');
      });
  });

  // TODO: per page currently does not work
  // https://issues.redhat.com/browse/PROJQUAY-4663
  // it('deletes repositories pagination', () => {
  //     cy.visit('/organization/manyrepositories');
  //     cy.get('button[id="toolbar-dropdown-checkbox"]').click();
  //     cy.contains('Select all').click();
  //     cy.contains('Actions').click();
  //     cy.contains('Delete').click();
  // })

  it('makes multiple repositories public', () => {
    cy.visit('/repository');
    cy.get('#repositorylist-search-input').type('user1');
    cy.get('button[id="toolbar-dropdown-checkbox"]').click();
    cy.contains('Select page (2)').click();
    cy.contains('Actions').click();
    cy.contains('Make public').click();
    cy.contains('Make repositories public');
    cy.contains(
      'Update 2 repositories visibility to be public so they are visible to all user, and may be pulled by all users.',
    );
    cy.contains('Make public').click();
    cy.contains('private').should('not.exist');
  });

  it('makes multiple repositories private', () => {
    cy.visit('/repository');
    cy.get('#repositorylist-search-input').type('projectquay');
    cy.get('button[id="toolbar-dropdown-checkbox"]').click();
    cy.contains('Select page (20)').click();
    cy.contains('Actions').click();
    cy.contains('Make private').click();
    cy.contains('Make repositories private');
    cy.contains(
      'Update 20 repositories visibility to be private so they are only visible to certain users, and only may be pulled by certain users.',
    );
    cy.contains('Make private').click();
    cy.contains('public').should('not.exist');
  });

  it('searches by name', () => {
    cy.visit('/repository');
    cy.get('#repositorylist-search-input').type('hello');
    cy.get('td[data-label="Name"]')
      .filter(':contains("hello-world")')
      .should('have.length', 2);
  });

  it('searches by name via regex', () => {
    cy.visit('/repository');
    cy.get('[id="filter-input-advanced-search"]').should('not.exist');
    cy.get('[aria-label="Open advanced search"]').click();
    cy.get('[id="filter-input-advanced-search"]').should('be.visible');
    cy.get('[id="filter-input-regex-checker"]').click();
    cy.get('#repositorylist-search-input').type('repo[0-9]$');
    cy.get('td[data-label="Name"]')
      .filter(':contains("repo1")')
      .should('exist');
    cy.get('td[data-label="Name"]')
      .filter(':contains("repo10")')
      .should('not.exist');
    cy.contains('1 - 9 of 9').should('exist');
    cy.get('[aria-label="Reset search"]').click();
    cy.get('td[data-label="Name"]')
      .filter(':contains("repo10")')
      .should('exist');
    cy.contains('1 - 20 of 156').should('exist');
  });

  it('searches by name including organization', () => {
    cy.visit('/repository');
    cy.get('#repositorylist-search-input').type('user1');
    cy.get('td[data-label="Name"]')
      .filter(':contains("user1")')
      .should('have.length', 2);
  });

  it('paginates repositories', () => {
    const repos: IRepository[] = [];
    for (let i = 0; i < 50; i++) {
      const repo = {
        namespace: 'manyrepositories',
        name: '',
        description: 'description',
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656432090,
        popularity: 0.0,
        is_starred: false,
      };
      repo.name = `repo${i}`;
      repos.push(repo);
    }
    cy.intercept(
      'GET',
      '/api/v1/repository?last_modified=true&namespace=*&public=true',
      {repositories: []},
    ).as('getRepositories');
    cy.intercept(
      'GET',
      '/api/v1/repository?last_modified=true&namespace=user1&public=true',
      {repositories: repos},
    ).as('getRepositories');
    cy.visit('/repository');
    cy.contains('1 - 20 of 50').should('exist');
    cy.get('td[data-label="Name"]').should('have.length', 20);

    // Change per page
    cy.get('button:contains("1 - 20 of 50")').first().click();
    cy.contains('20 per page').click();
    cy.get('td[data-label="Name"]').should('have.length', 20);

    // cycle through the pages
    cy.get('button[aria-label="Go to next page"]').first().click();
    cy.get('td[data-label="Name"]').should('have.length', 20);
    cy.get('button[aria-label="Go to next page"]').first().click();
    cy.get('td[data-label="Name"]').should('have.length', 10);

    // Go to first page
    cy.get('button[aria-label="Go to first page"]').first().click();
    cy.contains('repo0').should('exist');

    // Go to last page
    cy.get('button[aria-label="Go to last page"]').first().click();
    cy.contains('repo49').should('exist');

    // Switch per page while while being on a different page
    cy.get('button:contains("41 - 50 of 50")').first().click();
    cy.contains('20 per page').click();
    cy.contains('1 - 20 of 50').should('exist');
    cy.get('td[data-label="Name"]').should('have.length', 20);
  });

  it('renders many repositories', () => {
    const repos: IRepository[] = [];
    for (let i = 0; i < 1000; i++) {
      const repo = {
        namespace: 'manyrepositories',
        name: '',
        description: 'description',
        is_public: false,
        kind: 'image',
        state: 'NORMAL',
        quota_report: {
          quota_bytes: 132459661,
          configured_quota: 104857600,
        },
        last_modified: 1656432090,
        popularity: 0.0,
        is_starred: false,
      };
      repo.name = `repo${i}`;
      repos.push(repo);
    }
    cy.intercept(
      'GET',
      '/api/v1/repository?last_modified=true&namespace=*&public=true',
      {repositories: []},
    ).as('getRepositories');
    cy.intercept(
      'GET',
      '/api/v1/repository?last_modified=true&namespace=user1&public=true',
      {repositories: repos},
    ).as('getRepositories');
    cy.visit('/repository');
    cy.contains('1 - 20 of 1000').should('exist');
  });
});
