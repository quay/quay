/// <reference types="cypress" />

describe('Tests for Breadcrumbs', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Organization list page', () => {
    cy.visit('/organization');
    cy.get('nav[test-id="page-breadcrumbs-list"]').should('not.exist');
  });

  it('Repository list page', () => {
    cy.visit('/repository');
    cy.get('nav[test-id="page-breadcrumbs-list"]').should('not.exist');
  });

  it('Organization page', () => {
    cy.visit('/organization/projectquay');
    cy.get('nav[test-id="page-breadcrumbs-list"]').within(() => {
      cy.get('li')
        .each(($el, index) => {
          switch (index) {
            case 0:
              cy.wrap($el).should('have.text', 'organization');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/organization');
              break;
            case 1:
              cy.wrap($el).should('have.text', 'projectquay');
              cy.wrap($el).children('a').should('have.class', 'disabled-link');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/organization/projectquay');
              break;
          }
        })
        .then(($lis) => {
          expect($lis).to.have.length(2);
        });
    });
  });

  it('Repository page', () => {
    cy.visit('/repository/projectquay/repo1');
    cy.get('nav[test-id="page-breadcrumbs-list"]').within(() => {
      cy.get('li')
        .each(($el, index) => {
          switch (index) {
            case 0:
              cy.wrap($el).should('have.text', 'repository');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/repository');
              break;
            case 1:
              cy.wrap($el).should('have.text', 'projectquay');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/organization/projectquay');
              break;
            case 2:
              cy.wrap($el).should('have.text', 'repo1');
              cy.wrap($el).children('a').should('have.class', 'disabled-link');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/repository/projectquay/repo1');
              break;
          }
        })
        .then(($lis) => {
          expect($lis).to.have.length(3);
        });
    });
  });

  it('Tags list page', () => {
    cy.visit('/repository/user1/hello-world/tag/latest');
    cy.get('nav[test-id="page-breadcrumbs-list"]').within(() => {
      cy.get('li')
        .each(($el, index) => {
          switch (index) {
            case 0:
              cy.wrap($el).should('have.text', 'repository');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/repository');
              break;
            case 1:
              cy.wrap($el).should('have.text', 'user1');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/organization/user1');
              break;
            case 2:
              cy.wrap($el).should('have.text', 'hello-world');
              cy.wrap($el)
                .children('a')
                .should('have.attr', 'href', '/repository/user1/hello-world');
              break;
            case 3:
              cy.wrap($el).should('have.text', 'latest');
              cy.wrap($el).children('a').should('have.class', 'disabled-link');
              cy.wrap($el)
                .children('a')
                .should(
                  'have.attr',
                  'href',
                  '/repository/user1/hello-world/tag/latest',
                );
              break;
          }
        })
        .then(($lis) => {
          expect($lis).to.have.length(4);
        });
    });
  });
});
