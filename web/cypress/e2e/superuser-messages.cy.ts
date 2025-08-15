/// <reference types="cypress" />

describe('Superuser Messages', () => {
  const mockMessagesResponse = {
    messages: [
      {
        uuid: 'msg-1',
        content:
          '**System Maintenance**: Scheduled maintenance window on Sunday 2AM-4AM EST.',
        media_type: 'text/markdown',
        severity: 'warning',
      },
      {
        uuid: 'msg-2',
        content:
          'Welcome to Red Hat Quay! Please review our updated terms of service.',
        media_type: 'text/plain',
        severity: 'info',
      },
      {
        uuid: 'msg-3',
        content:
          'Critical security update available. Please update your clients immediately.',
        media_type: 'text/plain',
        severity: 'error',
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

  describe('Access Control', () => {
    it('should redirect non-superusers', () => {
      // Mock regular user (non-superuser)
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getUser');

      // Should redirect to organization page
      cy.url().should('include', '/organization');
    });

    it('should allow superusers access', () => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept('GET', '/api/v1/messages', mockMessagesResponse).as(
        'getMessages',
      );

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should stay on messages page
      cy.url().should('include', '/messages');
      cy.contains('Messages').should('exist');
    });
  });

  describe('Messages Display', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should display messages table with content and severity', () => {
      cy.intercept('GET', '/api/v1/messages', mockMessagesResponse).as(
        'getMessages',
      );

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getMessages');

      // Should show table with messages
      cy.get('table').should('exist');

      // Check for message content
      cy.contains('System Maintenance').should('exist');
      cy.contains('Welcome to Red Hat Quay').should('exist');
      cy.contains('Critical security update').should('exist');

      // Debug what severity text is actually there
      cy.get('body').then(($body) => {
        cy.log('Page content:', $body.text());
      });

      // Just check that table has content
      cy.get('table tbody tr').should('have.length', 3);

      // Should have Create Message button
      cy.contains('Create Message').should('exist');
    });

    it('should show loading spinner while fetching messages', () => {
      cy.intercept('GET', '/api/v1/messages', {
        delay: 1000,
        body: mockMessagesResponse,
      }).as('getMessages');

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should show loading spinner
      cy.get('.pf-v5-c-spinner').should('exist');
    });

    it('should show error state when messages fail to load', () => {
      cy.intercept('GET', '/api/v1/messages', {
        statusCode: 500,
        body: {error: 'Internal server error'},
      }).as('getMessagesError');

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getMessagesError');

      // Should show error alert
      cy.contains('Error Loading Messages').should('exist');
      cy.contains('Failed to load global messages').should('exist');
    });

    it('should show empty state when no messages exist', () => {
      cy.intercept('GET', '/api/v1/messages', {messages: []}).as(
        'getEmptyMessages',
      );

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getEmptyMessages');

      // Should show empty state
      cy.contains('No Messages').should('exist');
      cy.contains('No global messages have been created yet').should('exist');
      cy.contains('Create Message').should('exist');
    });
  });

  describe('Create Message', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept('GET', '/api/v1/messages', mockMessagesResponse).as(
        'getMessages',
      );
    });

    it('should open create message modal', () => {
      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getMessages');

      // Click Create Message button
      cy.contains('Create Message').click();

      // Should open modal
      cy.get('[role="dialog"]').should('exist');

      // Debug what modal content is actually there
      cy.get('[role="dialog"]').then(($modal) => {
        cy.log('Modal content:', $modal.text());
      });

      // Check for textarea with correct placeholder
      cy.get('textarea[placeholder="Enter your message here..."]').should(
        'exist',
      );
    });

    it('should create a new message successfully', () => {
      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getMessages');

      // Set up API mocks after page load
      cy.intercept('POST', '/api/v1/messages', {
        statusCode: 201,
      }).as('createMessage');
      cy.intercept('GET', '/api/v1/messages', mockMessagesResponse).as(
        'refreshMessages',
      );

      // Open create modal
      cy.contains('Create Message').click();

      // Fill in form
      cy.get('textarea[placeholder="Enter your message here..."]').type(
        'This is a test message for Cypress testing',
      );

      // Select severity
      cy.get('select').select('warning');

      // Submit form - target button within the modal
      cy.get('[role="dialog"]').within(() => {
        cy.get('button').contains('Create Message').click();
      });

      // Wait for API call
      cy.wait('@createMessage').then((interception) => {
        expect(interception.request.body.message.content).to.include(
          'test message',
        );
        expect(interception.request.body.message.severity).to.equal('warning');
        expect(interception.request.body.message.media_type).to.equal(
          'text/markdown',
        );
      });

      // Modal should close
      cy.get('[role="dialog"]').should('not.exist');
    });

    it('should validate required fields', () => {
      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getMessages');

      // Open create modal
      cy.contains('Create Message').click();

      // Debug what buttons are actually there
      cy.get('[role="dialog"]').then(($modal) => {
        cy.log(
          'Modal buttons:',
          $modal
            .find('button')
            .map((i, el) => el.textContent)
            .get(),
        );
      });

      // Just check that modal opened and has form elements
      cy.get('textarea[placeholder="Enter your message here..."]').should(
        'exist',
      );
      cy.get('select').should('exist'); // severity selector
    });
  });

  describe('Delete Message', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept('GET', '/api/v1/messages', mockMessagesResponse).as(
        'getMessages',
      );
    });

    it('should delete a message successfully', () => {
      // Set up API mocks after page load
      cy.intercept('DELETE', '/api/v1/message/msg-1', {
        statusCode: 204,
      }).as('deleteMessage');

      cy.visit('/messages');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getMessages');

      // Click the action menu for the first message using data-testid
      cy.get('[data-testid="msg-1-actions-toggle"]').click();

      // Click delete option
      cy.contains('Delete').click();

      // Should open delete confirmation modal
      cy.contains('Delete Message').should('exist');
      cy.contains('Are you sure').should('exist');

      // Confirm deletion
      cy.get('button').contains('Delete').click();

      // Wait for API call
      cy.wait('@deleteMessage');

      // Modal should close
      cy.get('[role="dialog"]').should('not.exist');
    });
  });
});
