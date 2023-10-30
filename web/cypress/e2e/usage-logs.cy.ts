describe('Usage Logs Export', () => {
  const aggregateLogsResp = {
    aggregated: [
      {
        kind: 'create_application',
        count: 1,
        datetime: new Date(),
      },
      {
        kind: 'org_create',
        count: 1,
        datetime: new Date(),
      },
    ],
  };

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('exports repository logs', () => {
    cy.intercept(
      'POST',
      'api/v1/repository/user1/hello-world/exportlogs?starttime=$endtime=',
    ).as('exportRepositoryLogs');
    cy.visit('/repository/user1/hello-world');
    cy.contains('Logs').click();
    cy.contains('Export').click();
    cy.get('[id="export-logs-callback"]').type('example@example.com');
    cy.contains('Confirm').click();
    cy.contains('Logs exported with id').should('be.visible');
  });
  it('exports repository logs failure', () => {
    cy.intercept(
      'POST',
      'api/v1/repository/user1/hello-world/exportlogs?starttime=$endtime=',
    ).as('exportRepositoryLogs');
    cy.visit('/repository/user1/hello-world');
    cy.contains('Logs').click();
    cy.contains('Export').click();
    cy.get('[id="export-logs-callback"]').type('blahblah');
    cy.contains('Confirm').should('be.disabled');
  });

  it('shows usage logs graph', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/aggregatelogs?*',
      aggregateLogsResp,
    );
    cy.visit('/organization/projectquay');
    cy.contains('Logs').click();
    cy.get('[class=pf-v5-c-chart]')
      .should('be.visible')
      .and((chart) => {
        expect(chart.height()).to.be.greaterThan(1);
      });
    cy.contains('Create Application').should('be.visible');
    cy.contains('Create organization').should('be.visible');
  });
});
