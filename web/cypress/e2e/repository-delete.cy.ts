describe('Repository Details Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    // Enable the repository settings feature
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        return res;
      }),
    ).as('getConfig');
    cy.visit('/repository/testorg/testrepo?tab=settings');
    cy.contains('Delete repository').click();
  });

  it('Deletes repository', () => {
    cy.contains(
      'Deleting a repository cannot be undone. Here be dragons!',
    ).should('exist');
    cy.contains('Delete Repository').click();
    cy.contains('Delete Repository?').should('exist');
    cy.contains(
      'You are requesting to delete the repository testorg/testrepo. This action is non-reversable.',
    ).should('exist');
    cy.contains(
      'You must type testorg/testrepo below to confirm deletion:',
    ).should('exist');
    cy.get('input[placeholder="Enter repository here"]').type(
      'testorg/testrepo',
    );
    cy.get('#delete-repository-modal').within(() =>
      cy.get('button').contains('Delete').click(),
    );
    cy.url().should('eq', `${Cypress.config('baseUrl')}/repository`);
    cy.contains('testrepo').should('not.exist');
  });
});
