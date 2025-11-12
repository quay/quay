/// <reference types="cypress" />

describe('Repository Mirroring', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    // Enable mirroring feature
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['REPO_MIRROR'] = true;
        return res;
      }),
    ).as('getConfig');
  });

  describe('Feature Flag Behavior', () => {
    it('should not show mirroring tab when REPO_MIRROR feature is disabled', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['REPO_MIRROR'] = false;
          return res;
        }),
      ).as('getConfigNoMirror');

      // Mock repository with MIRROR state
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      cy.visit('/repository/user1/hello-world');
      cy.wait('@getConfigNoMirror');
      cy.get('[data-testid="mirroring-tab"]').should('not.exist');
    });

    it('should show mirroring tab when REPO_MIRROR feature is enabled', () => {
      // Mock repository with MIRROR state
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      cy.visit('/repository/user1/hello-world');
      cy.wait('@getConfig');
      cy.get('[data-testid="mirroring-tab"]').should('exist');
    });
  });

  describe('Repository State Requirements', () => {
    it('should show state warning for non-mirror repositories', () => {
      // Mock repository with NORMAL state - using wildcard pattern to catch all variations
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'NORMAL',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      cy.contains("This repository's state is NORMAL").should('exist');
      cy.contains('Use the Settings tab and change it to Mirror').should(
        'exist',
      );
    });

    it('should show mirroring form for mirror repositories', () => {
      // Mock repository with MIRROR state - using wildcard pattern to catch all variations
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      // Mock no existing mirror config (404)
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 404,
      }).as('getMirrorConfig404');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      cy.contains('Repository Mirroring').should('exist');
      cy.contains('External Repository').should('exist');
      cy.get('[data-testid="mirror-form"]').should('exist');
    });
  });

  describe('New Mirror Configuration', () => {
    beforeEach(() => {
      // Mock repository with MIRROR state
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      // Mock no existing mirror config (404)
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world/mirror*', {
        statusCode: 404,
      }).as('getMirrorConfig404');

      // Mock robot accounts
      cy.intercept('GET', '/api/v1/organization/user1/robots*', {
        fixture: 'robots.json',
      }).as('getRobots');
    });

    it('should display new mirror form with correct initial state', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');

      // Wait for all API calls to complete (component should automatically stop loading)
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig404');
      cy.wait('@getRobots');
      // Note: Teams API may not be called immediately, test form loading first

      // Give component time to process 404 response and update loading state
      cy.wait(500);

      // Check form title and description
      cy.contains('External Repository').should('exist');
      cy.contains(
        'This feature will convert user1/hello-world into a mirror',
      ).should('exist');

      // For new mirrors, the enabled checkbox is NOT shown (only for existing configs)
      // Check for basic form fields that should be present
      cy.get('[data-testid="registry-location-input"]').should('exist');
      cy.get('[data-testid="tags-input"]').should('exist');

      // Check empty form fields
      cy.get('[data-testid="registry-location-input"]').should(
        'have.value',
        '',
      );
      cy.get('[data-testid="tags-input"]').should('have.value', '');
      cy.get('[data-testid="username-input"]').should('have.value', '');
      cy.get('[data-testid="password-input"]').should('have.value', '');

      // Check button says "Enable Mirror"
      cy.get('[data-testid="submit-button"]').should(
        'contain.text',
        'Enable Mirror',
      );
    });

    it('should validate required fields', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig404');
      cy.wait('@getRobots');

      // Submit button should be disabled initially
      cy.get('[data-testid="submit-button"]').should('be.disabled');

      // Fill in required fields one by one
      cy.get('[data-testid="registry-location-input"]').type(
        'quay.io/library/hello-world',
      );
      cy.get('[data-testid="submit-button"]').should('be.disabled');

      cy.get('[data-testid="tags-input"]').type('latest, stable');
      cy.get('[data-testid="submit-button"]').should('be.disabled');

      cy.get('[data-testid="sync-interval-input"]').type('60');
      cy.get('[data-testid="submit-button"]').should('be.disabled');

      // Select robot user
      cy.get('#robot-user-select').click();
      cy.contains('testorg+testrobot').click();

      // Now submit button should be enabled
      cy.get('[data-testid="submit-button"]').should('not.be.disabled');
    });

    it('should successfully create mirror configuration', () => {
      cy.intercept('POST', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 201,
        body: {
          is_enabled: true,
          external_reference: 'quay.io/library/hello-world',
          sync_status: 'NEVER_RUN',
          robot_username: 'testorg+testrobot',
        },
      }).as('createMirrorConfig');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      // Fill in the form
      cy.get('[data-testid="registry-location-input"]').type(
        'quay.io/library/hello-world',
      );
      cy.get('[data-testid="tags-input"]').type('latest, stable');
      cy.get('[data-testid="sync-interval-input"]').type('60');

      // Select robot user
      cy.get('#robot-user-select').click();
      cy.contains('testorg+testrobot').click();

      // Submit form
      cy.get('[data-testid="submit-button"]').click();

      cy.wait('@createMirrorConfig');
      cy.contains('Mirror configuration saved successfully').should('exist');
    });

    it('should handle form submission errors', () => {
      cy.intercept('POST', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 400,
        body: {message: 'Invalid external reference'},
      }).as('createMirrorConfigError');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      // Fill in the form with invalid data
      cy.get('[data-testid="registry-location-input"]').type(
        'invalid-registry',
      );
      cy.get('[data-testid="tags-input"]').type('latest');
      cy.get('[data-testid="sync-interval-input"]').type('60');

      // Select robot user
      cy.get('#robot-user-select').click();
      cy.contains('testorg+testrobot').click();

      // Submit form
      cy.get('[data-testid="submit-button"]').click();

      cy.wait('@createMirrorConfigError');
      cy.contains('Error saving mirror configuration').should('exist');
    });
  });

  describe('Existing Mirror Configuration', () => {
    beforeEach(() => {
      // Mock repository with MIRROR state
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      // Mock existing mirror config
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 200,
        body: {
          is_enabled: true,
          external_reference: 'quay.io/library/hello-world',
          external_registry_username: 'testuser',
          robot_username: 'user1+testrobot',
          sync_start_date: '2024-01-01T12:00:00Z',
          sync_interval: 3600,
          sync_status: 'SYNC_SUCCESS',
          last_sync: '2024-01-01T12:00:00Z',
          sync_expiration_date: null,
          sync_retries_remaining: 3,
          skopeo_timeout_interval: 300,
          external_registry_config: {
            verify_tls: true,
            unsigned_images: false,
            proxy: {
              http_proxy: null,
              https_proxy: null,
              no_proxy: null,
            },
          },
          root_rule: {
            rule_kind: 'tag_glob_csv',
            rule_value: ['latest', 'stable'],
          },
        },
      }).as('getMirrorConfig');
    });

    it('should load and display existing mirror configuration', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Check form is populated with existing data
      cy.get('[data-testid="mirror-enabled-checkbox"]').should('be.checked');
      cy.get('[data-testid="registry-location-input"]').should(
        'have.value',
        'quay.io/library/hello-world',
      );
      cy.get('[data-testid="tags-input"]').should(
        'have.value',
        'latest, stable',
      );
      cy.get('[data-testid="username-input"]').should('have.value', 'testuser');
      cy.get('[data-testid="sync-interval-input"]').should('have.value', '1');

      // Check button says "Update Mirror"
      cy.get('[data-testid="submit-button"]').should(
        'contain.text',
        'Update Mirror',
      );

      // Check configuration section title
      cy.contains('Configuration').should('exist');
    });

    it('should display status section for existing mirrors', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Check status section exists
      cy.contains('Status').should('exist');
      cy.contains('State').should('exist');
      cy.contains('Success').should('exist');
      cy.contains('Timeout').should('exist');
      cy.contains('Retries Remaining').should('exist');
      cy.contains('3 / 3').should('exist');
    });

    it('should enable/disable mirror configuration', () => {
      cy.intercept('PUT', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 201,
        body: {
          is_enabled: false,
          external_reference: 'quay.io/library/hello-world',
          sync_status: 'NEVER_RUN',
        },
      }).as('updateMirrorConfig');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Disable mirror
      cy.get('[data-testid="mirror-enabled-checkbox"]').uncheck();
      cy.contains('Scheduled mirroring disabled').should('exist');

      // Re-enable mirror
      cy.get('[data-testid="mirror-enabled-checkbox"]').check();
      cy.contains('Scheduled mirroring enabled').should('exist');
    });

    it('should update existing mirror configuration', () => {
      cy.intercept('PUT', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 201,
        body: {
          is_enabled: true,
          external_reference: 'quay.io/library/nginx',
          sync_status: 'NEVER_RUN',
        },
      }).as('updateMirrorConfig');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Update registry location
      cy.get('[data-testid="registry-location-input"]')
        .clear()
        .type('quay.io/library/nginx');

      // Submit form
      cy.get('[data-testid="submit-button"]').click();

      cy.wait('@updateMirrorConfig');
      cy.contains('Mirror configuration saved successfully').should('exist');
    });

    it('should preserve credentials when updating tag pattern without changing password (PROJQUAY-9608)', () => {
      cy.intercept(
        'PUT',
        '/api/v1/repository/user1/hello-world/mirror',
        (req) => {
          // Verify credentials are NOT sent when password is empty
          expect(req.body).to.not.have.property('external_registry_username');
          expect(req.body).to.not.have.property('external_registry_password');

          // Verify tag pattern update is sent
          expect(req.body.root_rule).to.deep.equal({
            rule_kind: 'tag_glob_csv',
            rule_value: ['latest', 'v*', '1.0'],
          });

          req.reply({
            statusCode: 201,
            body: {
              is_enabled: true,
              external_reference: 'quay.io/library/hello-world',
              external_registry_username: 'testuser',
              sync_status: 'NEVER_RUN',
              robot_username: 'user1+testrobot',
              sync_start_date: '2024-01-01T12:00:00Z',
              sync_interval: 3600,
              skopeo_timeout_interval: 300,
              external_registry_config: {
                verify_tls: true,
                unsigned_images: false,
                proxy: {
                  http_proxy: null,
                  https_proxy: null,
                  no_proxy: null,
                },
              },
              root_rule: {
                rule_kind: 'tag_glob_csv',
                rule_value: ['latest', 'v*', '1.0'],
              },
            },
          });
        },
      ).as('updateMirrorConfig');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Verify password field shows "None" (indicating empty value for existing config)
      cy.get('[data-testid="password-input"]').should('have.value', 'None');

      // Update tag pattern without changing password
      cy.get('[data-testid="tags-input"]').clear().type('latest, v*, 1.0');

      // Submit form
      cy.get('[data-testid="submit-button"]').click();

      cy.wait('@updateMirrorConfig');
      cy.contains('Mirror configuration saved successfully').should('exist');
    });

    it('should include credentials when password is provided during update', () => {
      cy.intercept(
        'PUT',
        '/api/v1/repository/user1/hello-world/mirror',
        (req) => {
          // Verify credentials ARE sent when password is filled in
          expect(req.body.external_registry_username).to.equal('newuser');
          expect(req.body.external_registry_password).to.equal('newpassword');

          req.reply({
            statusCode: 201,
            body: {
              is_enabled: true,
              external_reference: 'quay.io/library/hello-world',
              external_registry_username: 'newuser',
              sync_status: 'NEVER_RUN',
            },
          });
        },
      ).as('updateMirrorConfig');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Update credentials
      cy.get('[data-testid="username-input"]').clear().type('newuser');
      cy.get('[data-testid="password-input"]').type('newpassword');

      // Submit form
      cy.get('[data-testid="submit-button"]').click();

      cy.wait('@updateMirrorConfig');
      cy.contains('Mirror configuration saved successfully').should('exist');
    });
  });

  describe('Sync Operations', () => {
    beforeEach(() => {
      // Mock repository with MIRROR state
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');
    });

    it('should trigger sync now operation', () => {
      // Mock mirror config with sync capability
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 200,
        body: {
          is_enabled: true,
          external_reference: 'quay.io/library/hello-world',
          sync_status: 'NEVER_RUN',
          robot_username: 'testorg+testrobot',
          sync_start_date: '2024-01-01T12:00:00Z',
          sync_interval: 3600,
          skopeo_timeout_interval: 300,
          external_registry_config: {
            verify_tls: true,
            unsigned_images: false,
            proxy: {http_proxy: null, https_proxy: null, no_proxy: null},
          },
          root_rule: {
            rule_kind: 'tag_glob_csv',
            rule_value: ['latest'],
          },
        },
      }).as('getMirrorConfig');

      cy.intercept(
        'POST',
        '/api/v1/repository/user1/hello-world/mirror/sync-now',
        {
          statusCode: 204,
        },
      ).as('syncNow');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Click sync now button
      cy.get('[data-testid="sync-now-button"]').click();

      cy.wait('@syncNow');
      cy.contains('Sync scheduled successfully').should('exist');
    });

    it('should cancel ongoing sync operation', () => {
      // Mock mirror config with ongoing sync
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 200,
        body: {
          is_enabled: true,
          external_reference: 'quay.io/library/hello-world',
          sync_status: 'SYNCING',
          robot_username: 'testorg+testrobot',
          sync_start_date: '2024-01-01T12:00:00Z',
          sync_interval: 3600,
          skopeo_timeout_interval: 300,
          external_registry_config: {
            verify_tls: true,
            unsigned_images: false,
            proxy: {http_proxy: null, https_proxy: null, no_proxy: null},
          },
          root_rule: {
            rule_kind: 'tag_glob_csv',
            rule_value: ['latest'],
          },
        },
      }).as('getMirrorConfig');

      cy.intercept(
        'POST',
        '/api/v1/repository/user1/hello-world/mirror/sync-cancel',
        {
          statusCode: 204,
        },
      ).as('cancelSync');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfig');

      // Check sync status shows syncing
      cy.contains('Syncing').should('exist');

      // Click cancel button
      cy.get('[data-testid="cancel-sync-button"]').click();

      cy.wait('@cancelSync');
      cy.contains('Sync cancelled successfully').should('exist');
    });

    it('should disable sync/cancel buttons appropriately', () => {
      // Mock mirror config with different states
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 200,
        body: {
          is_enabled: true,
          external_reference: 'quay.io/library/hello-world',
          sync_status: 'SYNCING',
          robot_username: 'user1+testrobot',
          sync_start_date: '2024-01-01T12:00:00Z',
          sync_interval: 3600,
          skopeo_timeout_interval: 300,
          external_registry_config: {
            verify_tls: true,
            unsigned_images: false,
            proxy: {http_proxy: null, https_proxy: null, no_proxy: null},
          },
          root_rule: {
            rule_kind: 'tag_glob_csv',
            rule_value: ['latest'],
          },
        },
      }).as('getMirrorConfigSyncing');

      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getMirrorConfigSyncing');

      // When syncing: Sync Now should be disabled, Cancel should be enabled
      cy.get('[data-testid="sync-now-button"]').should('be.disabled');
      cy.get('[data-testid="cancel-sync-button"]').should('not.be.disabled');
    });
  });

  describe('Robot User Selection', () => {
    beforeEach(() => {
      // Mock repository with MIRROR state
      cy.intercept('GET', '/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      // Mock no existing mirror config
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror*', {
        statusCode: 404,
      }).as('getMirrorConfig404');

      // Mock robot accounts
      cy.intercept('GET', '/api/v1/organization/user1/robots*', {
        fixture: 'robots.json',
      }).as('getRobots');
    });

    it('should display robot user dropdown with options', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getRobots');

      // Click robot user dropdown
      cy.get('#robot-user-select').click();

      cy.contains('Create robot account').should('exist');
      cy.contains('Robot accounts').should('exist');
      cy.contains('testorg+testrobot').should('exist');
    });

    it('should select robot user from dropdown', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');
      cy.wait('@getRobots');

      // Select robot user
      cy.get('#robot-user-select').click();
      cy.contains('testorg+testrobot').click();

      // Check selection is reflected
      cy.get('#robot-user-select input').should(
        'have.value',
        'testorg+testrobot',
      );
    });
  });

  describe('Advanced Settings', () => {
    beforeEach(() => {
      // Mock repository with MIRROR state
      cy.intercept('GET', '**/api/v1/repository/user1/hello-world*', {
        body: {
          name: 'hello-world',
          namespace: 'user1',
          state: 'MIRROR',
          kind: 'image',
          description: '',
          is_public: true,
          is_organization: false,
          is_starred: false,
          can_write: true,
          can_admin: true,
        },
      }).as('getRepo');

      // Mock no existing mirror config
      cy.intercept('GET', '/api/v1/repository/user1/hello-world/mirror', {
        statusCode: 404,
      }).as('getMirrorConfig404');
    });

    it('should configure TLS verification', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      // Check TLS verification checkbox
      cy.get('[data-testid="verify-tls-checkbox"]').should('not.be.checked');
      cy.get('[data-testid="verify-tls-checkbox"]').check();
      cy.get('[data-testid="verify-tls-checkbox"]').should('be.checked');
    });

    it('should configure unsigned images', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      // Check unsigned images checkbox
      cy.get('[data-testid="unsigned-images-checkbox"]').should(
        'not.be.checked',
      );
      cy.get('[data-testid="unsigned-images-checkbox"]').check();
      cy.get('[data-testid="unsigned-images-checkbox"]').should('be.checked');
    });

    it('should configure proxy settings', () => {
      cy.visit('/repository/user1/hello-world?tab=mirroring');
      cy.wait('@getRepo');

      // Fill in proxy settings
      cy.get('[data-testid="http-proxy-input"]').type(
        'http://proxy.example.com:8080',
      );
      cy.get('[data-testid="https-proxy-input"]').type(
        'https://proxy.example.com:8080',
      );
      cy.get('[data-testid="no-proxy-input"]').type('localhost,127.0.0.1');

      // Check values are set
      cy.get('[data-testid="http-proxy-input"]').should(
        'have.value',
        'http://proxy.example.com:8080',
      );
      cy.get('[data-testid="https-proxy-input"]').should(
        'have.value',
        'https://proxy.example.com:8080',
      );
      cy.get('[data-testid="no-proxy-input"]').should(
        'have.value',
        'localhost,127.0.0.1',
      );
    });
  });
});
