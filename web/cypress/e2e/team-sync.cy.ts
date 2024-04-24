/// <reference types="cypress" />

describe('OIDC Team Sync', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/api/v1/user/', {fixture: 'oidc-user.json'}).as(
      'getUser',
    );
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
      'getCsrfToken',
    );
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/robots?permissions=true&token=false',
      {fixture: 'teamsync-robots.json'},
    ).as('getRobots');
    cy.intercept('GET', '/api/v1/organization/teamsyncorg', {
      fixture: 'teamsyncorg.json',
    }).as('getOrg');
    cy.intercept('GET', '/api/v1/organization/teamsyncorg/prototypes', {
      prototypes: [],
    }).as('getPrototypes');
    cy.intercept('GET', '/api/v1/organization/teamsyncorg/aggregatelogs?*', {
      aggregated: [],
    }).as('getAggregateLogs');
    cy.intercept('GET', '/api/v1/organization/teamsyncorg/logs?*', {
      start_time: '',
      end_time: '',
      logs: [],
    }).as('getLogs');

    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsync-team-members.json',
      },
    ).as('getTeammembers');
  });

  it('Validate OIDC group name', () => {
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.get('#team-members-toolbar').within(() =>
      cy.get('button:contains("Enable Team Sync")').click(),
    );
    cy.get('#directory-sync-modal').contains(
      "Enter the group name you'd like to sync membership with:",
    );
    cy.get('button:contains("Enable Sync")').should('be.disabled');
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('random');
    cy.get('button:contains("Enable Sync")').should('not.be.disabled');

    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .clear();

    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type(' ');
    cy.get('button:contains("Enable Sync")').should('be.disabled');
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .clear();

    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('team_name');
    cy.get('button:contains("Enable Sync")').should('not.be.disabled');
  });

  it('Enable team sync', () => {
    cy.intercept(
      'POST',
      '/api/v1/organization/teamsyncorg/team/testteam/syncing',
      {
        statusCode: 200,
      },
    ).as('getTeamSyncSuccess');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.get('#team-members-toolbar').within(() =>
      cy.get('button:contains("Enable Team Sync")').click(),
    );
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('org_team_group');
    cy.get('button:contains("Enable Sync")').click();
    cy.wait('@getTeamSyncSuccess');
    cy.contains('Successfully updated team sync config');
    cy.contains('tr', 'teamsyncorg+robotacct');
  });

  it('Directory sync config for super user', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsynced-members-superuser.json',
      },
    ).as('getSycedTeamMembers');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.wait('@getSycedTeamMembers');
    cy.contains(
      'This team is synchronized with a group in oidc and its user membership is therefore read-only.',
    ).should('exist');
    cy.contains('Team Synchronization Config').should('exist');
    cy.contains('Bound to group').should('exist');
    cy.contains('testteam_teamsync_group').should('exist');
    cy.contains('Last Updated').should('exist');
    cy.contains('Never').should('exist');
    cy.contains('tr', 'teamsyncorg+robotacct');
  });

  it('Directory sync config for non super user', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsynced-members.json',
      },
    ).as('getSycedTeamMembers');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.wait('@getSycedTeamMembers');
    cy.contains(
      'This team is synchronized with a group in oidc and its user membership is therefore read-only.',
    ).should('exist');
    cy.contains('Team Synchronization Config').should('not.exist');
    cy.contains('Bound to group').should('not.exist');
    cy.contains('org:team').should('not.exist');
    cy.contains('Last Updated').should('not.exist');
    cy.contains('tr', 'teamsyncorg+robotacct');
    cy.contains('Remove Synchronization').should('not.exist');
  });

  it('Remove Directory Sync', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsynced-members-superuser.json',
      },
    ).as('getSycedTeamMembers');
    cy.intercept(
      'DELETE',
      '/api/v1/organization/teamsyncorg/team/testteam/syncing',
      {
        statusCode: 200,
      },
    ).as('deleteTeamSyncing');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.wait('@getSycedTeamMembers');
    cy.contains('button', 'Remove synchronization').click();
    cy.contains('Remove Synchronization').should('exist');
    cy.contains(
      'Are you sure you want to disable group syncing on this team? The team will once again become editable.',
    ).should('exist');
    cy.contains('button', 'Confirm').click();
    cy.contains('Successfully removed team synchronization');
    cy.contains('tr', 'teamsyncorg+robotacct');
  });

  it('Empty state enable and remove team sync', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testempty/members?includePending=true',
      {
        fixture: 'emptystate-team-members.json',
      },
    ).as('getTeamMembers');
    cy.intercept(
      'POST',
      '/api/v1/organization/teamsyncorg/team/testempty/syncing',
      {
        statusCode: 200,
      },
    ).as('getTeamSyncSuccess');
    cy.intercept(
      'DELETE',
      '/api/v1/organization/teamsyncorg/team/testempty/syncing',
      {
        statusCode: 200,
      },
    ).as('deleteTeamSyncing');
    cy.visit(
      '/organization/teamsyncorg/teams/testempty?tab=Teamsandmembership',
    );
    cy.wait('@getTeamMembers');
    cy.contains('button', 'Enable Team Sync').click();
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('org_team_group');
    cy.get('button:contains("Enable Sync")').click();
    cy.wait('@getTeamSyncSuccess');
    cy.contains('Successfully updated team sync config');

    cy.contains('button', 'Remove synchronization').click();
    cy.contains('Remove Synchronization').should('exist');
    cy.contains(
      'Are you sure you want to disable group syncing on this team? The team will once again become editable.',
    ).should('exist');
    cy.contains('button', 'Confirm').click();
    cy.contains('Successfully removed team synchronization');
  });

  it('Verify delete option for users and robot accounts', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsynced-members-superuser.json',
      },
    ).as('getSycedTeamMembers');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.wait('@getSycedTeamMembers');
    cy.get('button[data-testid="teamsyncorg+robotacct-delete-icon"]').should(
      'exist',
    );
    cy.get('button[data-testid="teamsyncorg+test_robot-delete-icon"]').should(
      'exist',
    );
    cy.get('button[data-testid="admin-delete-icon"]').should('not.exist');
  });

  it('Verify oidc azure login modal', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsync-azure.json',
      },
    ).as('getAzureTeamMembers');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.wait('@getAzureTeamMembers');
    cy.get('button:contains("Enable Team Sync")').click();
    cy.get('#directory-sync-modal').contains(
      "Enter the group Object Id you'd like to sync membership with:",
    );
  });

  it('Verify Invited tab is disabled for a team that is synced', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/teamsyncorg/team/testteam/members?includePending=true',
      {
        fixture: 'teamsynced-members-superuser.json',
      },
    ).as('getSycedTeamMembers');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.wait('@getSycedTeamMembers');
    cy.get(`[data-testid="Invited"]`).find('button').should('be.disabled');
  });
});
