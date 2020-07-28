import { vendor } from "postcss";

/**
 * An element which displays the mirroring panel for a repository view.
 */
angular.module('quay').directive('repoPanelMirror', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-view/repo-panel-mirroring.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'isEnabled': '=isEnabled'
    },
    controllerAs: 'vm',
    controller: function ($scope, ApiService, Features) {

      let vm = this;

      // Feature Flagged
      if (!Features.REPO_MIRROR) { return; }

      // Shared by API Calls
      let params = { 'repository': $scope.repository.namespace + '/' + $scope.repository.name };

      /**
       * Mirror Configuration
       */
      vm.isSetup = false;
      vm.expirationDate = null;
      vm.isEnabled = null;
      vm.httpProxy = null;
      vm.httpsProxy = null;
      vm.externalReference = null;
      vm.noProxy = null;
      vm.retriesRemaining = null;
      vm.robot = null;
      vm.status = null;
      vm.syncInterval = null;
      vm.syncStartDate = moment().unix();
      vm.tags = null;
      vm.username = null;
      vm.verifyTLS = null;

      /**
       * Fetch the latest Repository Mirror Configuration
       */
      vm.getMirror = function() {
        ApiService.getRepoMirrorConfig(null, params)
        .then(function (resp) {
          vm.isSetup = true;

          vm.isEnabled = resp.is_enabled;
          vm.externalReference = resp.external_reference;
          vm.syncInterval = resp.sync_interval;
          vm.username = resp.external_registry_username;
          vm.syncStartDate = resp.sync_start_date;
          vm.status = resp.sync_status;
          vm.expirationDate = resp.sync_expiration_date;
          vm.retriesRemaining = resp.sync_retries_remaining;

          vm.robot = {};
          if (resp.robot_username) {
            vm.robot = {
              'name': resp.robot_username,
              'kind': 'user',
              'is_robot': true
            };
          }

          vm.tags = resp.root_rule.rule_value || [];

          // TODO: These are not consistently provided by the API. Correct that in the API.
          vm.verifyTLS = resp.external_registry_config.verify_tls;
          if (resp.external_registry_config.proxy) {
            vm.httpProxy = resp.external_registry_config.proxy.http_proxy;
            vm.httpsProxy = resp.external_registry_config.proxy.https_proxy;
            vm.noProxy = resp.external_registry_config.proxy.no_proxy;
          }
        }, function (err) { console.info("No repository mirror configuration.", err); });
      }

      /**
       * Human-friendly status messages
       */
      vm.statusLabels = {
        "NEVER_RUN": "Scheduled",
        "SYNC_NOW": "Scheduled Now",
        "SYNCING": "Sync In Progress",
        "SUCCESS": "Last Sync Succeeded",
        "FAIL": "Last Sync Failed"
      }

      /**
       * Convert (Unix) Timestamp to ISO Formatted Date String used by the API
       */
      vm.timestampToISO = function(ts) {
        let dt = moment.unix(ts).toISOString().split('.')[0] + 'Z'; // Remove milliseconds
        return dt;
      }

      /**
       * Convert ISO Date String to (Unix) Timestamp
       */
      vm.timestampFromISO = function(dt) {
        let ts = moment(dt).unix();
        return ts;
      }

      /**
       * When set to a truthy value, any `cor-confirm-dialog` associated with these variables will
       * be displayed.
       */
      vm.credentialsChanges = null;
      vm.httpProxyChanges = null;
      vm.httpsProxyChanges = null;
      vm.locationChanges = null;
      vm.noProxyChanges = null;
      vm.syncIntervalChanges = null;
      vm.syncStartDateChanges = null;
      vm.tagChanges = null;

      /**
       * The following `show` functions initialize and trigger the display of a modal to modify
       * configuration attributes.
       */

      vm.showChangeSyncInterval = function() {
        vm.syncIntervalChanges = {
          'fieldName': 'synchronization interval',
          'values': {
            'sync_interval': vm.syncInterval
          }
        }
      }

      vm.showChangeSyncStartDate = function() {
        let ts = vm.timestampFromISO(vm.syncStartDate);
        vm.syncStartDateChanges = {
          'fieldName': 'next synchronization date',
          'values': {
            'sync_start_date': ts
          }
        }
      }

      vm.showChangeTags = function() {
        vm.tagChanges = {
          'fieldName': 'tag patterns',
          'values': {
            'rule_value': vm.tags || []
          }
        }
      }

      vm.showChangeCredentials = function() {
        vm.credentialsChanges = {
          'fieldName': 'credentials',
          'values': {
            'external_registry_username': vm.username,
            'external_registry_password': null
          }
        }
      }

      vm.showChangeHTTPProxy = function() {
        vm.httpProxyChanges = {
          'fieldName': 'HTTP Proxy',
          'values': {
            'external_registry_config': {
              'proxy': {
                'http_proxy': vm.httpProxy
              }
            }
          }
        }
      }

      vm.showChangeHTTPsProxy = function() {
        vm.httpsProxyChanges = {
          'fieldName': 'HTTPs Proxy',
          'values': {
            'external_registry_config': {
              'proxy': {
                'https_proxy': vm.httpsProxy
              }
            }
          }
        }
      }

      vm.showChangeNoProxy = function() {
        vm.noProxyChanges = {
          'fieldName': 'No Proxy',
          'values': {
            'external_registry_config': {
              'proxy': {
                'no_proxy': vm.noProxy
              }
            }
          }
        }
      }

      vm.showChangeExternalRepository = function() {
        vm.externalRepositoryChanges = {
          'fieldName': 'External Repository',
          'values': {
            'external_reference': vm.externalReference
          }
        }
      }

      /**
       * Submit API request to modify repository mirroring attribute(s)
       */
      vm.changeConfig = function(data, callback) {

        let fieldName = data.fieldName || 'configuration';
        let requestBody = data.values;
        let errMsg = "Unable to change " + fieldName + '.';
        let handleError = ApiService.errorDisplay(errMsg, callback);

        let handleSuccess = function() {
          vm.getMirror(); // Fetch updated configuration
          if (callback) callback(true);
        }

        ApiService.changeRepoMirrorConfig(requestBody, params)
          .then(handleSuccess, handleError);

        return true;
      }

      /**
       * Transform the DatePicker's Unix timestamp into a string compatible with the API
       * before attempting to change it.
       */
      vm.changeSyncStartDate = function(data, callback) {
        let newSyncStartDate = vm.timestampToISO(data.values.sync_start_date);
        data.values.sync_start_date = newSyncStartDate;
        return vm.changeConfig(data, callback);
      }

      /**
       * Enable `Verify TLS`.
       */
      vm.enableVerifyTLS = function() {
        let data = {
          'fieldName': 'TLS verification',
          'values': {
            'external_registry_config': {
              'verify_tls': true
            }
          }
        }

        return vm.changeConfig(data, null);
      }

      /**
       * Disable `Verify TLS`
       */
      vm.disableVerifyTLS = function() {
        let data = {
          'fieldName': 'TLS verification',
          'values': {
            'external_registry_config': {
              'verify_tls': false
            }
          }
        }

        return vm.changeConfig(data, null);
      }

      /**
       * Toggle `Verify TLS`.
       */
      vm.toggleVerifyTLS = function() {
        if (vm.verifyTLS) return vm.disableVerifyTLS();
        else return vm.enableVerifyTLS();
      }

      /**
       *  Change Robot user.
       */
      vm.changeRobot = function(robot) {
        if (!vm.robot) return;
        if (!robot || robot.name == vm.robot.name) return;

        let data = {
          'fieldName': 'robot',
          'values': {
            'robot_username': robot.name
          }
        }

        return vm.changeConfig(data, null)
      }

      /**
       * Delete Credentials
       */
      vm.deleteCredentials = function() {
        let data = {
          'fieldName': 'credentials',
          'values': {
            'external_registry_username': null,
            'external_registry_password': null
          }
        }

        return vm.changeConfig(data, null);
      }

      /**
       * Enable mirroring configuration.
       */
      vm.enableMirroring = function() {
        let data = {
          'fieldName': 'enabled state',
          'values': {
            'is_enabled': true
          }
        }

        return vm.changeConfig(data, null)
      }

      /**
       * Disable mirroring configuration.
       */
      vm.disableMirroring = function() {
        let data = {
          'fieldName': 'enabled state',
          'values': {
            'is_enabled': false
          }
        }

        return vm.changeConfig(data, null)
      }

      /**
       * Toggle mirroring on/off.
       */
      vm.toggleMirroring = function() {
        if (vm.isEnabled) return vm.disableMirroring();
        else return vm.enableMirroring();
      }

      /**
       * Update Tag-Rules
       */
      vm.changeTagRules = function(data, callback) {
        let csv = data.values.rule_value,
            patterns;

        // If already an array then the data has not changed
        if (Array.isArray(csv)) {
          patterns = csv;
        } else {
          patterns = csv.split(',').map(s => s.trim());
        }


        patterns.map(s => s.trim()); // Trim excess whitespace
        patterns = Array.from(new Set(patterns)); // De-duplicate

        if (patterns.length < 1) {
          bootbox.alert('Rule value required');
          callback(false);
          return false;
        }

        data = {
          'root_rule': {
            'rule_kind': "tag_glob_csv",
            'rule_value': patterns
          }
        }

        let displayError = ApiService.errorDisplay('Could not change Tag Rules', callback);

        ApiService
        .changeRepoMirrorConfig(data, params)
        .then(function(resp) {
          vm.getMirror();
          callback(true);
        }, displayError);

        return true;
      }

      /**
       * Trigger Immediate Synchronization
       */
      vm.syncNow = function () {
        let displayError = ApiService.errorDisplay('Unable to sync now', null);

        ApiService
          .syncNow(null, params)
          .then(function(resp) {
            vm.getMirror(); // Reload latest changes
            return true;
          }, displayError);

        return true;
      }

      /**
       * Cancel In-Progress Synchronization
       */
      vm.syncCancel = function() {
        let displayError = ApiService.errorDisplay('Unable to cancel sync', null);

        ApiService
          .syncCancel(null, params)
          .then(function(resp) {
            vm.getMirror(); // Reload latest changes
            return true;
          }, displayError);

        return true;
      }

      // Load the current mirror configuration on initialization
      if ($scope.repository.state == 'MIRROR') {
        vm.getMirror();
      }

      /**
       * Configure mirroing.
       * TODO: Move this, and the associated template/view, to its own component and use the
       *       wizard-flow instead of a single form.
       */
      vm.setupMirror = function() {

        // Apply transformations
        let syncStartDate = vm.timestampToISO(vm.syncStartDate || moment().unix());
        let patterns = Array.from(new Set(vm.tags.split(',').map(s => s.trim()))); // trim + de-dupe

        let requestBody = {
           'external_reference': vm.externalReference,
           'external_registry_username': vm.username,
           'external_registry_password': vm.password,
           'sync_interval': vm.syncInterval,
           'sync_start_date': syncStartDate,
           'robot_username': vm.robot.name,
           'external_registry_config': {
             'verify_tls': vm.verifyTLS || false, // `null` not allowed
             'proxy': {
               'http_proxy': vm.httpProxy,
               'https_proxy': vm.httpsProxy,
               'no_proxy': vm.noProxy
             }
           },
           'root_rule': {
             'rule_kind': "tag_glob_csv",
             'rule_value': patterns
           }
        }

        let successHandler = function(resp) { vm.getMirror(); return true; }
        let errorHandler  = ApiService.errorDisplay('Unable to setup mirror.', null);
        ApiService.createRepoMirrorConfig(requestBody, params).then(successHandler, errorHandler);

      }
    }
  };
  return directiveDefinitionObject;
});
