/// <reference types="cypress" />

describe('OIDC Team Sync', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
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
      cy.get('button:contains("Enable Directory Sync")').click(),
    );
    cy.get('#oidc-team-sync-helper-text').contains(
      'The expected OIDC group name format is - org_name:team_name. Must match ^[a-z0-9][a-z0-9]+:[a-z0-9]+$',
    );
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('random');
    cy.get('button:contains("Enable Sync")').should('be.disabled');
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .clear();

    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('1:1');
    cy.get('button:contains("Enable Sync")').should('be.disabled');
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .clear();

    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('org:team');
    cy.get('button:contains("Enable Sync")').should('not.be.disabled');
  });

  it('Enable directory sync', () => {
    cy.intercept(
      'POST',
      '/api/v1/organization/teamsyncorg/team/testteam/syncing',
      {
        statusCode: 200,
      },
    ).as('getTeamSyncSuccess');
    cy.visit('/organization/teamsyncorg/teams/testteam?tab=Teamsandmembership');
    cy.get('#team-members-toolbar').within(() =>
      cy.get('button:contains("Enable Directory Sync")').click(),
    );
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('org:team');
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
    cy.contains('Directory Synchronization Config').should('exist');
    cy.contains('Bound to group').should('exist');
    cy.contains('teamsyncorg:groupname').should('exist');
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
    cy.contains('Directory Synchronization Config').should('not.exist');
    cy.contains('Bound to group').should('not.exist');
    cy.contains('org:team').should('not.exist');
    cy.contains('Last Updated').should('not.exist');
    cy.contains('tr', 'teamsyncorg+robotacct');
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
    cy.contains('button', 'Enable Directory Sync').click();
    cy.get('#directory-sync-modal')
      .find('input[id="team-sync-group-name"]')
      .type('org:team');
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
});
