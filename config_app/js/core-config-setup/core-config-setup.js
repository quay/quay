import * as URI from 'urijs';
import * as angular from 'angular';
const templateUrl = require('./config-setup-tool.html');
const urlParsedField =  require('../config-field-templates/config-parsed-field.html');
const urlVarField = require('../config-field-templates/config-variable-field.html');
const urlListField = require('../config-field-templates/config-list-field.html');
const urlFileField = require('../config-field-templates/config-file-field.html');
const urlBoolField = require('../config-field-templates/config-bool-field.html');
const urlNumericField = require('../config-field-templates/config-numeric-field.html');
const urlContactField = require('../config-field-templates/config-contact-field.html');
const urlContactsField = require('../config-field-templates/config-contacts-field.html');
const urlMapField = require('../config-field-templates/config-map-field.html');
const urlServiceKeyField = require('../config-field-templates/config-service-key-field.html');
const urlStringField = require('../config-field-templates/config-string-field.html');
const urlPasswordField = require('../config-field-templates/config-password-field.html');

const urlStringListField = require('../config-field-templates/config-string-list-field.html');
const urlCertField = require('../config-field-templates/config-certificates-field.html');


angular.module("quay-config")
  .directive('configSetupTool', () => {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl,
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {
        'isActive': '=isActive',
        'configurationSaved': '&configurationSaved',
        'setupCompleted': '&setupCompleted',
      },
      controller: function($rootScope, $scope, $element, $timeout, ApiService) {
        var authPassword = null;

        $scope.HOSTNAME_REGEX = '^[a-zA-Z-0-9\.]+(:[0-9]+)?$';
        $scope.GITHOST_REGEX = '^https?://([a-zA-Z0-9]+\.?\/?)+$';

        // Determines if a particular field should be marked as "read-only".
        // The __read_only_fields is populated using environment variables.
        // This is usually used for the case where an external system is
        // managing part of the configuration.
        $scope.isFieldReadonly = function(field) {
            return window.__read_only_fields.includes(field);
        }

        $scope.SERVICES = [
          {'id': 'redis', 'title': 'Redis'},

          {'id': 'registry-storage', 'title': 'Registry Storage'},

          {'id': 'time-machine', 'title': 'Time Machine'},

          {'id': 'access', 'title': 'Access Settings'},

          {'id': 'ssl', 'title': 'SSL certificate and key', 'condition': function(config) {
            return config.PREFERRED_URL_SCHEME == 'https';
          }},

          {'id': 'ldap', 'title': 'LDAP Authentication', 'condition': function(config) {
            return config.AUTHENTICATION_TYPE == 'LDAP';
          }},

          {'id': 'jwt', 'title': 'JWT Authentication', 'condition': function(config) {
            return config.AUTHENTICATION_TYPE == 'JWT';
          }},

          {'id': 'keystone', 'title': 'Keystone Authentication', 'condition': function(config) {
            return config.AUTHENTICATION_TYPE == 'Keystone';
          }},

          {'id': 'apptoken-auth', 'title': 'App Token Authentication', 'condition': function(config) {
            return config.AUTHENTICATION_TYPE == 'AppToken';
          }},

          {'id': 'github-login', 'title': 'Github (Enterprise) Authentication', 'condition': function(config) {
            return config.FEATURE_GITHUB_LOGIN;
          }},

          {'id': 'google-login', 'title': 'Google Authentication', 'condition': function(config) {
            return config.FEATURE_GOOGLE_LOGIN;
          }},

          {'id': 'github-trigger', 'title': 'GitHub (Enterprise) Build Triggers', 'condition': function(config) {
            return config.FEATURE_GITHUB_BUILD;
          }},

          {'id': 'bitbucket-trigger', 'title': 'BitBucket Build Triggers', 'condition': function(config) {
            return config.FEATURE_BITBUCKET_BUILD;
          }},

          {'id': 'gitlab-trigger', 'title': 'GitLab Build Triggers', 'condition': function(config) {
            return config.FEATURE_GITLAB_BUILD;
          }},

          {'id': 'security-scanner', 'title': 'Quay Security Scanner', 'condition': function(config) {
            return config.FEATURE_SECURITY_SCANNER;
          }},

          {'id': 'oidc-login', 'title': 'OIDC Login(s)', 'condition': function(config) {
            return $scope.getOIDCProviders(config).length > 0;
          }},

          {'id': 'actionlogarchiving', 'title': 'Action Log Rotation', 'condition': function(config) {
            return config.FEATURE_ACTION_LOG_ROTATION;
          }},

          {'id': 'repomirroring', 'title': 'Repository Mirroring', 'condition': function(config) {
            return config.FEATURE_REPOSITORY_MIRRORING;
          }},

          {'id': 'elasticsearch', 'title': 'Elasticsearch', 'condition': function(config) {
            return config.LOGS_MODEL == 'elasticsearch';
          }},

          {'id': 'kinesis', 'title': 'Kinesis', 'condition': function(config) {
            return config.LOGS_MODEL_CONFIG.producer == 'kinesis_stream';
          }},
        ];

        $scope.STORAGE_CONFIG_FIELDS = {
          'LocalStorage': [
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/some/directory', 'kind': 'text'}
          ],

          'S3Storage': [
            {'name': 's3_bucket', 'title': 'S3 Bucket',  'placeholder': 'my-cool-bucket', 'kind': 'text'},
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/path/inside/bucket', 'kind': 'text'},
            {'name': 's3_access_key', 'title': 'AWS Access Key (optional if using IAM)', 'placeholder': 'accesskeyhere', 'kind': 'text', 'optional': true},
            {'name': 's3_secret_key', 'title': 'AWS Secret Key (optional if using IAM)', 'placeholder': 'secretkeyhere', 'kind': 'password', 'optional': true},
            {'name': 'host', 'title': 'S3 Host', 'placeholder': 's3.amazonaws.com', 'kind': 'text', 'optional': true},
            {'name': 'port', 'title': 'S3 Port', 'placeholder': '443', 'kind': 'text', 'pattern': '^[0-9]+$', 'optional': true}
          ],

          'AzureStorage': [
            {'name': 'azure_container', 'title': 'Azure Storage Container', 'placeholder': 'container', 'kind': 'text'},
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/path/inside/container', 'kind': 'text'},
            {'name': 'azure_account_name', 'title': 'Azure Account Name', 'placeholder': 'accountnamehere', 'kind': 'text'},
            {'name': 'azure_account_key', 'title': 'Azure Account Key',  'placeholder': 'accountkeyhere', 'kind': 'text', 'optional': true},
            {'name': 'sas_token', 'title': 'Azure SAS Token',  'placeholder': 'sastokenhere', 'kind': 'text', 'optional': true},
          ],

          'GoogleCloudStorage': [
            {'name': 'access_key', 'title': 'Cloud Access Key', 'placeholder': 'accesskeyhere', 'kind': 'text'},
            {'name': 'secret_key', 'title': 'Cloud Secret Key', 'placeholder': 'secretkeyhere', 'kind': 'text'},
            {'name': 'bucket_name', 'title': 'GCS Bucket',  'placeholder': 'my-cool-bucket', 'kind': 'text'},
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/path/inside/bucket', 'kind': 'text'}
          ],

          'RHOCSStorage': [
            {'name': 'hostname', 'title': 'NooBaa Server Hostname', 'placeholder': 'my.noobaa.hostname', 'kind': 'text'},
            {'name': 'port', 'title': 'Custom Port (optional)', 'placeholder': '443', 'kind': 'text', 'pattern': '^[0-9]+$', 'optional': true},
            {'name': 'is_secure', 'title': 'Is Secure', 'placeholder': 'Require SSL', 'kind': 'bool'},
            {'name': 'access_key', 'title': 'Access Key', 'placeholder': 'accesskeyhere', 'kind': 'text'},
            {'name': 'secret_key', 'title': 'Secret Key', 'placeholder': 'secretkeyhere', 'kind': 'text'},
            {'name': 'bucket_name', 'title': 'Bucket Name',  'placeholder': 'my-cool-bucket', 'kind': 'text'},
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/path/inside/bucket', 'kind': 'text'}
          ],

          'RadosGWStorage': [
            {'name': 'hostname', 'title': 'Rados Server Hostname', 'placeholder': 'my.rados.hostname', 'kind': 'text'},
            {'name': 'port', 'title': 'Custom Port (optional)', 'placeholder': '443', 'kind': 'text', 'pattern': '^[0-9]+$', 'optional': true},
            {'name': 'is_secure', 'title': 'Is Secure', 'placeholder': 'Require SSL', 'kind': 'bool'},
            {'name': 'access_key', 'title': 'Access Key', 'placeholder': 'accesskeyhere', 'kind': 'text', 'help_url': 'http://ceph.com/docs/master/radosgw/admin/'},
            {'name': 'secret_key', 'title': 'Secret Key', 'placeholder': 'secretkeyhere', 'kind': 'text'},
            {'name': 'bucket_name', 'title': 'Bucket Name',  'placeholder': 'my-cool-bucket', 'kind': 'text'},
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/path/inside/bucket', 'kind': 'text'}
          ],

          'SwiftStorage': [
            {'name': 'auth_version', 'title': 'Swift Auth Version', 'kind': 'option', 'values': [1, 2, 3]},
            {'name': 'auth_url', 'title': 'Swift Auth URL', 'placeholder': 'http://swiftdomain/auth/v1.0', 'kind': 'text'},
            {'name': 'swift_container', 'title': 'Swift Container Name', 'placeholder': 'mycontainer', 'kind': 'text',
             'help_text': 'The swift container for all objects. Must already exist inside Swift.'},

            {'name': 'storage_path', 'title': 'Storage Path', 'placeholder': '/path/inside/container', 'kind': 'text'},

            {'name': 'swift_user', 'title': 'Username', 'placeholder': 'accesskeyhere', 'kind': 'text',
             'help_text': 'Note: For Swift V1, this is "username:password" (-U on the CLI).'},
            {'name': 'swift_password', 'title': 'Key/Password', 'placeholder': 'secretkeyhere', 'kind': 'text',
             'help_text': 'Note: For Swift V1, this is the API token (-K on the CLI).'},

            {'name': 'ca_cert_path', 'title': 'CA Cert Filename', 'placeholder': 'conf/stack/swift.cert', 'kind': 'text', 'optional': true},

            {'name': 'temp_url_key', 'title': 'Temp URL Key (optional)', 'placholder': 'key-here', 'kind': 'text', 'optional': true,
             'help_url': 'https://coreos.com/products/enterprise-registry/docs/latest/swift-temp-url.html',
             'help_text': 'If enabled, will allow for faster pulls directly from Swift.'},

            {'name': 'os_options', 'title': 'OS Options', 'kind': 'map',
             'keys': ['tenant_id', 'auth_token', 'service_type', 'endpoint_type', 'tenant_name', 'object_storage_url', 'region_name',
                      'project_id', 'project_name', 'project_domain_name', 'user_domain_name', 'user_domain_id']}
          ],

          'CloudFrontedS3Storage': [
            {'name': 's3_bucket', 'title': 'S3 Bucket',  'placeholder': 'my-cool-bucket', 'kind': 'text'},
            {'name': 'storage_path', 'title': 'Storage Directory', 'placeholder': '/path/inside/bucket', 'kind': 'text'},
            {'name': 's3_access_key', 'title': 'AWS Access Key (optional if using IAM)', 'placeholder': 'accesskeyhere', 'kind': 'text', 'optional': true},
            {'name': 's3_secret_key', 'title': 'AWS Secret Key (optional if using IAM)', 'placeholder': 'secretkeyhere', 'kind': 'text', 'optional': true},
            {'name': 'host', 'title': 'S3 Host', 'placeholder': 's3.amazonaws.com', 'kind': 'text', 'optional': true},
            {'name': 'port', 'title': 'S3 Port', 'placeholder': '443', 'kind': 'text', 'pattern': '^[0-9]+$', 'optional': true},

            {'name': 'cloudfront_distribution_domain', 'title': 'CloudFront Distribution Domain Name', 'placeholder': 'somesubdomain.cloudfront.net', 'pattern': '^([0-9a-zA-Z]+\\.)+[0-9a-zA-Z]+$', 'kind': 'text'},
            {'name': 'cloudfront_key_id', 'title': 'CloudFront Key ID', 'placeholder': 'APKATHISISAKEYID', 'kind': 'text'},
            {'name': 'cloudfront_privatekey_filename', 'title': 'CloudFront Private Key', 'filesuffix': 'cloudfront-signing-key.pem', 'kind': 'file'},
          ],
        };

        $scope.enableFeature = function(config, feature) {
          config[feature] = true;
        };

        $scope.validateHostname = function(hostname) {
          if (hostname.indexOf('127.0.0.1') == 0 || hostname.indexOf('localhost') == 0) {
            return 'Please specify a non-localhost hostname. "localhost" will refer to the container, not your machine.';
          }

          return null;
        };

        $scope.config = null;
        $scope.originalConfig = null;
        $scope.mapped = {
          '$hasChanges': false
        };

        $scope.hasfile = {};
        $scope.validating = null;
        $scope.savingConfiguration = false;

        $scope.removeOIDCProvider = function(provider) {
          delete $scope.config[provider];
        };

        $scope.addOIDCProvider = () => {
          bootbox.prompt('Enter an ID for the OIDC provider', function(result) {
            if (!result) {
              return;
            }

            result = result.toUpperCase();

            if (!result.match(/^[A-Z0-9]+$/)) {
              bootbox.alert('Invalid ID for OIDC provider: must be alphanumeric');
              return;
            }

            if (result == 'GITHUB' || result == 'GOOGLE') {
              bootbox.alert('Invalid ID for OIDC provider: cannot be a reserved name');
              return;
            }

            var key = result + '_LOGIN_CONFIG';
            if ($scope.config[key]) {
              bootbox.alert('Invalid ID for OIDC provider: already exists');
              return;
            }

            $scope.config[key] = {};
          });
        };

        $scope.getOIDCProviderId = function(key) {
          var index = key.indexOf('_LOGIN_CONFIG');
          if (index <= 0) {
            return null;
          }

          return key.substr(0, index).toLowerCase();
        };

        $scope.getOIDCProviders = function(config) {
          var keys = Object.keys(config || {});
          return keys.filter(function(key) {
            if (key == 'GITHUB_LOGIN_CONFIG' || key == 'GOOGLE_LOGIN_CONFIG') {
              // Has custom UI and config.
              return false;
            }

            return !!$scope.getOIDCProviderId(key);
          });
        };

        $scope.getServices = function(config) {
          var services = [];
          if (!config) { return services; }

          for (var i = 0; i < $scope.SERVICES.length; ++i) {
            var service = $scope.SERVICES[i];
            if (!service.condition || service.condition(config)) {
              services.push({
                'service': service,
                'status': 'validating'
              });
            }
          }

          return services;
        };

        $scope.validationStatus = function(serviceInfos) {
          if (!serviceInfos) { return 'validating'; }

          var hasError = false;
          for (var i = 0; i < serviceInfos.length; ++i) {
            if (serviceInfos[i].status == 'validating') {
              return 'validating';
            }
            if (serviceInfos[i].status == 'error') {
              hasError = true;
            }
          }

          return hasError ? 'failed' : 'success';
        };

        $scope.cancelValidation = function() {
          $('#validateAndSaveModal').modal('hide');
          $scope.validating = null;
          $scope.savingConfiguration = false;
        };

        $scope.validateService = function(serviceInfo, opt_password) {
          var params = {
            'service': serviceInfo.service.id
          };

          var data = {
            'config': $scope.config,
            'password': opt_password || ''
          };

          var errorDisplay = ApiService.errorDisplay(
              'Could not validate configuration. Please report this error.',
              function() {
                authPassword = null;
              });

          ApiService.scValidateConfig(data, params).then(function(resp) {
            serviceInfo.status = resp.status ? 'success' : 'error';
            serviceInfo.errorMessage = $.trim(resp.reason || '');

            if (!resp.status) {
              authPassword = null;
            }

          }, errorDisplay);
        };

        $scope.checkValidateAndSave = function() {
          if ($scope.configform.$valid) {
            saveStorageConfig();
            $scope.validateAndSave();
            return;
          }

          var query = $element.find("input.ng-invalid:first");

          if (query && query.length) {
            query[0].scrollIntoView();
            query.focus();
          }
        };

        $scope.validateAndSave = function() {
          $scope.validating = $scope.getServices($scope.config);

          $scope.performValidateAndSave();
        };

        $scope.performValidateAndSave = function(opt_password) {
          $scope.savingConfiguration = false;
          $scope.validating = $scope.getServices($scope.config);

          authPassword = opt_password;

          $('#validateAndSaveModal').modal({
            keyboard: false,
            backdrop: 'static'
          });

          for (var i = 0; i < $scope.validating.length; ++i) {
            var serviceInfo = $scope.validating[i];
            $scope.validateService(serviceInfo, opt_password);
          }
        };

        $scope.saveConfiguration = function() {
          $scope.savingConfiguration = true;

          // Make sure to note that fully verified setup is completed. We use this as a signal
          // in the setup tool.
          $scope.config['SETUP_COMPLETE'] = true;

          var data = {
            'config': $scope.config,
            'hostname': window.location.host,
            'password': authPassword || ''
          };

          var errorDisplay = ApiService.errorDisplay(
            'Could not save configuration. Please report this error.',
            function() {
              authPassword = null;
            });

          ApiService.scUpdateConfig(data).then(function(resp) {
            authPassword = null;

            $scope.savingConfiguration = false;
            $scope.mapped.$hasChanges = false;

            $('#validateAndSaveModal').modal('hide');

            $scope.setupCompleted();
          }, errorDisplay);
        };

        // Convert storage config to an array
        var initializeStorageConfig = function($scope) {
          var config = $scope.config.DISTRIBUTED_STORAGE_CONFIG || {};
          var defaultLocations = $scope.config.DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS || [];
          var preference = $scope.config.DISTRIBUTED_STORAGE_PREFERENCE || [];

          $scope.serverStorageConfig = angular.copy(config);
          $scope.storageConfig = [];

          Object.keys(config).forEach(function(location) {
            $scope.storageConfig.push({
              location: location,
              defaultLocation: defaultLocations.indexOf(location) >= 0,
              data: angular.copy(config[location]),
              error: {},
            });
          });

          if (!$scope.storageConfig.length) {
            $scope.addStorageConfig('default');
            return;
          }

          // match DISTRIBUTED_STORAGE_PREFERENCE order first, remaining are
          // ordered by unicode point value
          $scope.storageConfig.sort(function(a, b) {
            var indexA = preference.indexOf(a.location);
            var indexB = preference.indexOf(b.location);

            if (indexA > -1 && indexB > -1) return indexA < indexB ? -1 : 1;
            if (indexA > -1) return -1;
            if (indexB > -1) return 1;

            return a.location < b.location ? -1 : 1;
          });
        };

        $scope.allowChangeLocationStorageConfig = function(location) {
          if (!$scope.serverStorageConfig[location]) { return true };

          // allow user to change location ID if another exists with the same ID
          return $scope.storageConfig.filter(function(sc) {
            return sc.location === location;
          }).length >= 2;
        };

        $scope.allowRemoveStorageConfig = function(location) {
          return $scope.storageConfig.length > 1 && $scope.allowChangeLocationStorageConfig(location);
        };

        $scope.canAddStorageConfig = function() {
          return $scope.config &&
            $scope.config.FEATURE_STORAGE_REPLICATION &&
            $scope.storageConfig &&
            (!$scope.storageConfig.length || $scope.storageConfig.length < 10);
        };

        $scope.addStorageConfig = function(location) {
          var storageType = 'LocalStorage';

          // Use last storage type by default
          if ($scope.storageConfig.length) {
            storageType = $scope.storageConfig[$scope.storageConfig.length-1].data[0];
          }

          $scope.storageConfig.push({
            location: location || '',
            defaultLocation: false,
            data: [storageType, {}],
            error: {},
          });
        };

        $scope.removeStorageConfig = function(sc) {
          $scope.storageConfig.splice($scope.storageConfig.indexOf(sc), 1);
        };

        var saveStorageConfig = function() {
          var config = {};
          var defaultLocations = [];
          var preference = [];

          $scope.storageConfig.forEach(function(sc) {
            config[sc.location] = sc.data;
            if (sc.defaultLocation) defaultLocations.push(sc.location);
            preference.push(sc.location);
          });

          $scope.config.DISTRIBUTED_STORAGE_CONFIG = config;
          $scope.config.DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS = defaultLocations;
          $scope.config.DISTRIBUTED_STORAGE_PREFERENCE = preference;
        };

        var gitlabSelector = function(key) {
          return function(value) {
            if (!value || !$scope.config) { return; }

            if (!$scope.config[key]) {
              $scope.config[key] = {};
            }

            if (value == 'enterprise') {
              if ($scope.config[key]['GITLAB_ENDPOINT'] == 'https://gitlab.com/') {
                $scope.config[key]['GITLAB_ENDPOINT'] = '';
              }
            } else if (value == 'hosted') {
              $scope.config[key]['GITLAB_ENDPOINT'] = 'https://gitlab.com/';
            }
          };
        };

        var githubSelector = function(key) {
          return function(value) {
            if (!value || !$scope.config) { return; }

            if (!$scope.config[key]) {
              $scope.config[key] = {};
            }

            if (value == 'enterprise') {
              if ($scope.config[key]['GITHUB_ENDPOINT'] == 'https://github.com/') {
                $scope.config[key]['GITHUB_ENDPOINT'] = '';
              }
              delete $scope.config[key]['API_ENDPOINT'];
            } else if (value == 'hosted') {
              $scope.config[key]['GITHUB_ENDPOINT'] = 'https://github.com/';
              $scope.config[key]['API_ENDPOINT'] = 'https://api.github.com/';
            }
          };
        };

        var getKey = function(config, path) {
          if (!config) {
            return null;
          }

          var parts = path.split('.');
          var current = config;
          for (var i = 0; i < parts.length; ++i) {
            var part = parts[i];
            if (!current[part]) { return null; }
            current = current[part];
          }
          return current;
        };

        var initializeMappedLogic = function(config) {
          var gle = getKey(config, 'GITHUB_LOGIN_CONFIG.GITHUB_ENDPOINT');
          var gte = getKey(config, 'GITHUB_TRIGGER_CONFIG.GITHUB_ENDPOINT');

          $scope.mapped['GITHUB_LOGIN_KIND'] = gle == 'https://github.com/' ? 'hosted' : 'enterprise';
          $scope.mapped['GITHUB_TRIGGER_KIND'] = gte == 'https://github.com/' ? 'hosted' : 'enterprise';

          var glabe = getKey(config, 'GITLAB_TRIGGER_KIND.GITHUB_ENDPOINT');
          $scope.mapped['GITLAB_TRIGGER_KIND'] = glabe == 'https://gitlab.com/' ? 'hosted' : 'enterprise';

          $scope.mapped['redis'] = {};
          $scope.mapped['redis']['host'] = getKey(config, 'BUILDLOGS_REDIS.host') || getKey(config, 'USER_EVENTS_REDIS.host');
          $scope.mapped['redis']['port'] = getKey(config, 'BUILDLOGS_REDIS.port') || getKey(config, 'USER_EVENTS_REDIS.port');
          $scope.mapped['redis']['password'] = getKey(config, 'BUILDLOGS_REDIS.password') || getKey(config, 'USER_EVENTS_REDIS.password');

          $scope.mapped['TLS_SETTING'] = 'none';
          if (config['PREFERRED_URL_SCHEME'] == 'https') {
            if (config['EXTERNAL_TLS_TERMINATION'] === true) {
              $scope.mapped['TLS_SETTING'] = 'external-tls';
            } else {
              $scope.mapped['TLS_SETTING'] = 'internal-tls';
            }
          }

          $scope.mapped['LOGS_MODEL_CONFIG'] = {};
          $scope.mapped['LOGS_MODEL'] = config['LOGS_MODEL'] || 'database';
          if (config['LOGS_MODEL'] == 'elasticsearch') {
            $scope.mapped['LOGS_MODEL_CONFIG']['producer'] = config['LOGS_MODEL_CONFIG']['producer'] || 'elasticsearch';

            if (config['LOGS_MODEL_CONFIG']['kinesis_stream_config']) {
              $scope.mapped['LOGS_MODEL_CONFIG']['kinesis_stream_config'] = config['LOGS_MODEL_CONFIG']['kinesis_stream_config'];
            }

            if (config['LOGS_MODEL_CONFIG']['elasticsearch_config']) {
              $scope.mapped['LOGS_MODEL_CONFIG']['elasticsearch_config'] = config['LOGS_MODEL_CONFIG']['elasticsearch_config'];
            }
          }
        };

        var tlsSetter = function(value) {
          if (value == null || !$scope.config) { return; }

          switch (value) {
            case 'none':
              $scope.config['PREFERRED_URL_SCHEME'] = 'http';
              delete $scope.config['EXTERNAL_TLS_TERMINATION'];
              return;

            case 'external-tls':
              $scope.config['PREFERRED_URL_SCHEME'] = 'https';
              $scope.config['EXTERNAL_TLS_TERMINATION'] = true;
              return;

            case 'internal-tls':
              $scope.config['PREFERRED_URL_SCHEME'] = 'https';
              delete $scope.config['EXTERNAL_TLS_TERMINATION'];
              return;
          }
        };

        var redisSetter = function(keyname) {
          return function(value) {
            if (value == null || !$scope.config) { return; }

            if (!$scope.config['BUILDLOGS_REDIS']) {
              $scope.config['BUILDLOGS_REDIS'] = {};
            }

            if (!$scope.config['USER_EVENTS_REDIS']) {
              $scope.config['USER_EVENTS_REDIS'] = {};
            }

            if (!value) {
              delete $scope.config['BUILDLOGS_REDIS'][keyname];
              delete $scope.config['USER_EVENTS_REDIS'][keyname];
              return;
            }

            $scope.config['BUILDLOGS_REDIS'][keyname] = value;
            $scope.config['USER_EVENTS_REDIS'][keyname] = value;
          };
        };

        var logsModelSelector = function(keyname) {
          return function(value) {
            if (!$scope.config) { return; }

            if (!value) { $scope.config['LOGS_MODEL'] = 'database'; };

            if (value == 'elasticsearch') {
              $scope.config['LOGS_MODEL'] = 'elasticsearch';
              if (!$scope.config['LOGS_MODEL_CONFIG']) {
                $scope.config['LOGS_MODEL_CONFIG'] = {};
              }
              if (!$scope.config['LOGS_MODEL_CONFIG']['elasticsearch_config']) {
                $scope.config['LOGS_MODEL_CONFIG']['elasticsearch_config'] = {};
              }
              if (!$scope.config['LOGS_MODEL_CONFIG']['producer']) {
                $scope.mapped['LOGS_MODEL_CONFIG']['producer'] = 'elasticsearch';
                $scope.config['LOGS_MODEL_CONFIG']['producer'] = 'elasticsearch';
              }
            } else if (value == 'database') {
              $scope.config['LOGS_MODEL'] = 'database';
              $scope.mapped['LOGS_MODEL_CONFIG'] = {};
              $scope.config['LOGS_MODEL_CONFIG'] = {};
            }
            console.log("TEST:", $scope.config);
          };
        };

        var logsProducerSetter = function(value) {
          if (value == null || !$scope.config ) { return; }

          if (value == 'kinesis_stream') {
            if (!$scope.config['LOGS_MODEL_CONFIG']['kinesis_stream_config']) {
              $scope.config['LOGS_MODEL_CONFIG']['kinesis_stream_config'] = {};
            }
          } else {
            delete $scope.mapped['LOGS_MODEL_CONFIG']['kinesis_stream_config'];
            delete $scope.config['LOGS_MODEL_CONFIG']['kinesis_stream_config'];
          }

          $scope.config['LOGS_MODEL_CONFIG']['producer'] = value;
        };

        var logsModelConfigSetter = function(keyname, configName) {
          return function(value) {
            if (value == null || !$scope.config ) { return; }

            if (!$scope.config['LOGS_MODEL_CONFIG'][configName]) {
              $scope.config['LOGS_MODEL_CONFIG'][configName] = {};
            }

            if (!value) {
              delete $scope.config['LOGS_MODEL_CONFIG'][configName][keyname];
            }

            $scope.config['LOGS_MODEL_CONFIG'][configName][keyname] = value;
          };
        };

        // Add mapped logic.
        $scope.$watch('mapped.GITHUB_LOGIN_KIND', githubSelector('GITHUB_LOGIN_CONFIG'));
        $scope.$watch('mapped.GITHUB_TRIGGER_KIND', githubSelector('GITHUB_TRIGGER_CONFIG'));
        $scope.$watch('mapped.GITLAB_TRIGGER_KIND', gitlabSelector('GITLAB_TRIGGER_KIND'));
        $scope.$watch('mapped.TLS_SETTING', tlsSetter);

        $scope.$watch('mapped.redis.host', redisSetter('host'));
        $scope.$watch('mapped.redis.port', redisSetter('port'));
        $scope.$watch('mapped.redis.password', redisSetter('password'));

        $scope.$watch('mapped.LOGS_MODEL', logsModelSelector('LOGS_MODEL'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.producer', logsProducerSetter);
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.elasticsearch_config.host', logsModelConfigSetter('host', 'elasticsearch_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.elasticsearch_config.port', logsModelConfigSetter('port', 'elasticsearch_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.elasticsearch_config.access_key', logsModelConfigSetter('access_key', 'elasticsearch_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.elasticsearch_config.secret_key', logsModelConfigSetter('secret_key', 'elasticsearch_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.elasticsearch_config.aws_region', logsModelConfigSetter('aws_region', 'elasticsearch_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.elasticsearch_config.index_prefix', logsModelConfigSetter('index_prefix', 'elasticsearch_config'));

        $scope.$watch('mapped.LOGS_MODEL_CONFIG.kinesis_stream_config.aws_access_key', logsModelConfigSetter('aws_access_key', 'kinesis_stream_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.kinesis_stream_config.aws_secret_key', logsModelConfigSetter('aws_secret_key', 'kinesis_stream_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.kinesis_stream_config.aws_region', logsModelConfigSetter('aws_region', 'kinesis_stream_config'));
        $scope.$watch('mapped.LOGS_MODEL_CONFIG.kinesis_stream_config.stream_name', logsModelConfigSetter('stream_name', 'kinesis_stream_config'));

        // Remove extra extra fields (which are not allowed) from storage config.
        var updateFields = function(sc) {
          var type = sc.data[0];
          var configObject = sc.data[1];
          var allowedFields = $scope.STORAGE_CONFIG_FIELDS[type];

          // Remove any fields not allowed.
          for (var fieldName in configObject) {
            if (!configObject.hasOwnProperty(fieldName)) {
              continue;
            }

            var isValidField = $.grep(allowedFields, function(field) {
              return field.name == fieldName;
            }).length > 0;

            if (!isValidField) {
              delete configObject[fieldName];
            }
          }

          // Set any missing boolean fields to false.
          for (var i = 0; i < allowedFields.length; ++i) {
            if (allowedFields[i].kind == 'bool') {
              configObject[allowedFields[i].name] = configObject[allowedFields[i].name] || false;
            }
          }
        };

        // Validate and update storage config on update.
        var refreshStorageConfig = function() {
          if (!$scope.config || !$scope.storageConfig) return;

          var locationCounts = {};
          var errors = [];
          var valid = true;

          $scope.storageConfig.forEach(function(sc) {
            // remove extra fields from storage config
            updateFields(sc);

            if (!locationCounts[sc.location]) locationCounts[sc.location] = 0;
            locationCounts[sc.location]++;
          });

          // validate storage config
          $scope.storageConfig.forEach(function(sc) {
            var error = {};

            if ($scope.config.FEATURE_STORAGE_REPLICATION && sc.data[0] === 'LocalStorage') {
              error.engine = 'Replication to a locally mounted directory is unsupported as it is only accessible on a single machine.';
              valid = false;
            }

            if (locationCounts[sc.location] > 1) {
              error.location = 'Location ID must be unique.';
              valid = false;
            }

            errors.push(error);
          });

          $scope.storageConfigError = errors;
          $scope.configform.$setValidity('storageConfig', valid);
        };

        $scope.$watch('config.INTERNAL_OIDC_SERVICE_ID', function(service_id) {
          if (service_id) {
            $scope.config['FEATURE_DIRECT_LOGIN'] = false;
          }
        });

        $scope.$watch('config.FEATURE_STORAGE_REPLICATION', function() {
          refreshStorageConfig();
        });

        $scope.$watch('config.FEATURE_USER_CREATION', function(value) {
          if (!value) {
            $scope.config['FEATURE_INVITE_ONLY_USER_CREATION'] = false;
          }
        });

        $scope.$watch('config.LOGS_MODEL', function(value) {
          if (!value) {
            $scope.config['LOGS_MODEL'] = 'database';
          }
        });

        $scope.$watch('storageConfig', function() {
          refreshStorageConfig();
        }, true);

        $scope.$watch('config', function(value) {
          $scope.mapped['$hasChanges'] = true;
        }, true);

        $scope.$watch('isActive', function(value) {
          if (!value) { return; }

          ApiService.scGetConfig().then(function(resp) {
            $scope.config = resp['config'] || {};
            $scope.originalConfig = Object.assign({}, resp['config'] || {});;
            initializeMappedLogic($scope.config);
            initializeStorageConfig($scope);
            $scope.mapped['$hasChanges'] = false;
          }, ApiService.errorDisplay('Could not load config'));
        });
      }
    };

    return directiveDefinitionObject;
  })

  .directive('configParsedField', function ($timeout) {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlParsedField,
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'parser': '&parser',
        'serializer': '&serializer'
      },
      controller: function($scope, $element, $transclude) {
        $scope.childScope = null;

        $transclude(function(clone, scope) {
          $scope.childScope = scope;
          $scope.childScope['fields'] = {};
          $element.append(clone);
        });

        $scope.childScope.$watch('fields', function(value) {
          // Note: We need the timeout here because Angular starts the digest of the
          // parent scope AFTER the child scope, which means it can end up one action
          // behind. The timeout ensures that the parent scope will be fully digest-ed
          // and then we update the binding. Yes, this is a hack :-/.
          $timeout(function() {
            $scope.binding = $scope.serializer({'fields': value});
          });
        }, true);

        $scope.$watch('binding', function(value) {
          var parsed = $scope.parser({'value': value});
          for (var key in parsed) {
            if (parsed.hasOwnProperty(key)) {
             $scope.childScope['fields'][key] = parsed[key];
            }
          }
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configVariableField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlVarField,
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'binding': '=binding'
      },
      controller: function($scope, $element) {
        $scope.sections = {};
        $scope.currentSection = null;

        $scope.setSection = function(section) {
          $scope.binding = section.value;
        };

        this.addSection = function(section, element) {
          $scope.sections[section.value] = {
            'title': section.valueTitle,
            'value': section.value,
            'element': element
          };

          element.hide();

          if (!$scope.binding) {
            $scope.binding = section.value;
          }
        };

        $scope.$watch('binding', function(binding) {
          if (!binding) { return; }

          if ($scope.currentSection) {
            $scope.currentSection.element.hide();
          }

          if ($scope.sections[binding]) {
            $scope.sections[binding].element.show();
            $scope.currentSection = $scope.sections[binding];
          }
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('variableSection', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlVarField,
      priority: 1,
      require: '^configVariableField',
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'value': '@value',
        'valueTitle': '@valueTitle'
      },
      controller: function($scope, $element) {
        var parentCtrl = $element.parent().controller('configVariableField');
        parentCtrl.addSection($scope, $element);
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configListField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlListField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'placeholder': '@placeholder',
        'defaultValue': '@defaultValue',
        'itemTitle': '@itemTitle',
        'itemPattern': '@itemPattern'
      },
      controller: function($scope, $element) {
        $scope.removeItem = function(item) {
          var index = $scope.binding.indexOf(item);
          if (index >= 0) {
            $scope.binding.splice(index, 1);
          }
        };

        $scope.addItem = function() {
          if (!$scope.newItemName) {
            return;
          }

          if (!$scope.binding) {
            $scope.binding = [];
          }

          if ($scope.binding.indexOf($scope.newItemName) >= 0) {
            return;
          }

          $scope.binding.push($scope.newItemName);
          $scope.newItemName = null;
        };

        $scope.patternMap = {};

        $scope.getRegexp = function(pattern) {
          if (!pattern) {
            pattern = '.*';
          }

          if ($scope.patternMap[pattern]) {
            return $scope.patternMap[pattern];
          }

          return $scope.patternMap[pattern] = new RegExp(pattern);
        };

        $scope.$watch('binding', function(binding) {
          if (!binding && $scope.defaultValue) {
            $scope.binding = eval($scope.defaultValue);
          }
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configFileField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlFileField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'filename': '@filename',
        'skipCheckFile': '@skipCheckFile',
        'hasFile': '=hasFile',
        'binding': '=?binding'
      },
      controller: function($scope, $element, Restangular, $upload) {
        $scope.hasFile = false;

        var setHasFile = function(hasFile) {
          $scope.hasFile = hasFile;
          $scope.binding = hasFile ? $scope.filename : null;
        };

        $scope.onFileSelect = function(files) {
          if (files.length < 1) {
            setHasFile(false);
            return;
          }

          $scope.uploadProgress = 0;
          $scope.upload = $upload.upload({
            url: '/api/v1/superuser/config/file/' + $scope.filename,
            method: 'POST',
            data: {'_csrf_token': window.__token},
            file: files[0],
          }).progress(function(evt) {
            $scope.uploadProgress = parseInt(100.0 * evt.loaded / evt.total);
            if ($scope.uploadProgress == 100) {
              $scope.uploadProgress = null;
              setHasFile(true);
            }
          }).success(function(data, status, headers, config) {
            $scope.uploadProgress = null;
            setHasFile(true);
          });
        };

        var loadStatus = function(filename) {
          Restangular.one('superuser/config/file/' + filename).get().then(function(resp) {
            setHasFile(false);
          });
        };

        if ($scope.filename && $scope.skipCheckFile != "true") {
          loadStatus($scope.filename);
        }
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configBoolField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlBoolField,
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'binding': '=binding'
      },
      controller: function($scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configNumericField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlNumericField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'placeholder': '@placeholder',
        'defaultValue': '@defaultValue',
        'isReadonly': '=?isReadonly',
      },
      controller: function($scope, $element) {
        $scope.bindinginternal = 0;

        $scope.$watch('binding', function(binding) {
          if ($scope.binding == 0 && $scope.defaultValue) {
            $scope.binding = $scope.defaultValue * 1;
          }

          $scope.bindinginternal = $scope.binding;
        });

        $scope.$watch('bindinginternal', function(binding) {
          var newValue = $scope.bindinginternal * 1;
          if (isNaN(newValue)) {
            newValue = 0;
          }
          $scope.binding = newValue;
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configContactsField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlContactsField,
      priority: 1,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding'
      },
      controller: function($scope, $element) {
        var padItems = function(items) {
          // Remove the last item if both it and the second to last items are empty.
          if (items.length > 1 && !items[items.length - 2].value && !items[items.length - 1].value) {
            items.splice(items.length - 1, 1);
            return;
          }

          // If the last item is non-empty, add a new item.
          if (items.length == 0 || items[items.length - 1].value) {
            items.push({'value': ''});
            return;
          }
        };

        $scope.itemHash = null;
        $scope.$watch('items', function(items) {
          if (!items) { return; }
          padItems(items);

          var itemHash = '';
          var binding = [];
          for (var i = 0; i < items.length; ++i) {
            var item = items[i];
            if (item.value && (URI(item.value).host() || URI(item.value).path())) {
              binding.push(item.value);
              itemHash += item.value;
            }
          }

          $scope.itemHash = itemHash;
          $scope.binding = binding;
        }, true);

        $scope.$watch('binding', function(binding) {
          var current = binding || [];
          var items = [];
          var itemHash = '';
          for (var i = 0; i < current.length; ++i) {
            items.push({'value': current[i]})
            itemHash += current[i];
          }

          if ($scope.itemHash != itemHash) {
            $scope.items = items;
          }
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configContactField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlContactField,
      priority: 1,
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'binding': '=binding'
      },
      controller: function($scope, $element) {
        $scope.kind = null;
        $scope.value = null;

        var updateBinding = function() {
          if ($scope.value == null) { return; }
          var value = $scope.value || '';

          switch ($scope.kind) {
            case 'mailto':
              $scope.binding = 'mailto:' + value;
              return;

            case 'tel':
              $scope.binding = 'tel:' + value;
              return;

            case 'irc':
              $scope.binding = 'irc://' + value;
              return;

            default:
              $scope.binding = value;
              return;
          }
        };

        $scope.$watch('kind', updateBinding);
        $scope.$watch('value', updateBinding);

        $scope.$watch('binding', function(value) {
          if (!value) {
            $scope.kind = null;
            $scope.value = null;
            return;
          }

          var uri = URI(value);
          $scope.kind = uri.scheme();

          switch ($scope.kind) {
            case 'mailto':
            case 'tel':
              $scope.value = uri.path();
              break;

            case 'irc':
              $scope.value = value.substr('irc://'.length);
              break;

            default:
              $scope.kind = 'http';
              $scope.value = value;
              break;
          }
        });

        $scope.getPlaceholder = function(kind) {
          switch (kind) {
            case 'mailto':
              return 'some@example.com';

            case 'tel':
              return '555-555-5555';

            case 'irc':
              return 'myserver:port/somechannel';

            default:
              return 'http://some/url';
          }
        };
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configMapField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlMapField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'keys': '=keys'
      },
      controller: function($scope, $element) {
        $scope.newKey = null;
        $scope.newValue = null;

        $scope.hasValues = function(binding) {
          return binding && Object.keys(binding).length;
        };

        $scope.removeKey = function(key) {
          delete $scope.binding[key];
        };

        $scope.addEntry = function() {
          if (!$scope.newKey || !$scope.newValue) { return; }

          $scope.binding = $scope.binding || {};
          $scope.binding[$scope.newKey] = $scope.newValue;
          $scope.newKey = null;
          $scope.newValue = null;
        }
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configServiceKeyField', function (ApiService) {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlServiceKeyField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'serviceName': '@serviceName',
      },
      controller: function($scope, $element) {
        $scope.foundKeys = [];
        $scope.loading = false;
        $scope.loadError = false;
        $scope.hasValidKey = false;
        $scope.hasValidKeyStr = null;

        $scope.updateKeys = function() {
          $scope.foundKeys = [];
          $scope.loading = true;

          ApiService.listServiceKeys().then(function(resp) {
            $scope.loading = false;
            $scope.loadError = false;

            resp['keys'].forEach(function(key) {
              if (key['service'] == $scope.serviceName) {
                $scope.foundKeys.push(key);
              }
            });

            $scope.hasValidKey = checkValidKey($scope.foundKeys);
            $scope.hasValidKeyStr = $scope.hasValidKey ? 'true' : '';
          }, function() {
            $scope.loading = false;
            $scope.loadError = true;
          });
        };

        // Perform initial loading of the keys.
        $scope.updateKeys();

        $scope.isKeyExpired = function(key) {
          if (key.expiration_date != null) {
            var expiration_date = moment(key.expiration_date);
            return moment().isAfter(expiration_date);
          }
          return false;
        };

        $scope.showRequestServiceKey = function(opt_newKey) {
          $scope.requestKeyInfo = {
            'service': $scope.serviceName,
            'newKey': opt_newKey
          };
        };

        $scope.handleKeyCreated = function() {
          $scope.updateKeys();
        };

        var checkValidKey = function(keys) {
          for (var i = 0; i < keys.length; ++i) {
            var key = keys[i];
            if (!key.approval) {
              continue;
            }

            if ($scope.isKeyExpired(key)) {
              continue;
            }

            return true;
          }

          return false;
        };
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configStringField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlStringField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'placeholder': '@placeholder',
        'pattern': '@pattern',
        'defaultValue': '@defaultValue',
        'validator': '&validator',
        'isOptional': '=isOptional',
        'isReadonly': '=?isReadonly'
      },
      controller: function($scope, $element) {
        var firstSet = true;

        $scope.patternMap = {};

        $scope.getRegexp = function(pattern) {
          if (!pattern) {
            pattern = '.*';
          }

          if ($scope.patternMap[pattern]) {
            return $scope.patternMap[pattern];
          }

          return $scope.patternMap[pattern] = new RegExp(pattern);
        };

        $scope.$watch('binding', function(binding) {
          if (firstSet && !binding && $scope.defaultValue) {
            $scope.binding = $scope.defaultValue;
            firstSet = false;
          }

          $scope.errorMessage = $scope.validator({'value': binding || ''});
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configPasswordField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlPasswordField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'placeholder': '@placeholder',
        'defaultValue': '@defaultValue',
        'validator': '&validator',
        'isOptional': '=isOptional'
      },
      controller: function($scope, $element) {
        var firstSet = true;

        $scope.$watch('binding', function(binding) {
          if (firstSet && !binding && $scope.defaultValue) {
            $scope.binding = $scope.defaultValue;
            firstSet = false;
          }
          $scope.errorMessage = $scope.validator({'value': binding || ''});
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configStringListField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlStringListField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'binding': '=binding',
        'itemTitle': '@itemTitle',
        'itemDelimiter': '@itemDelimiter',
        'placeholder': '@placeholder',
        'isOptional': '=isOptional'
      },
      controller: function($scope, $element) {
        $scope.$watch('internalBinding', function(value) {
          if (value) {
            $scope.binding = value.split($scope.itemDelimiter);
          }
        });

        $scope.$watch('binding', function(value) {
          if (value) {
            $scope.internalBinding = value.join($scope.itemDelimiter);
          }
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('configCertificatesField', function () {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: urlCertField,
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
      },
      controller: function($scope, $element, $upload, ApiService, UserService) {
        $scope.resetUpload = 0;
        $scope.certsUploading = false;

        var loadCertificates = function() {
          $scope.certificatesResource = ApiService.getCustomCertificatesAsResource().get(function(resp) {
            $scope.certInfo = resp;
            $scope.certsUploading = false;
          });
        };

        loadCertificates();

        $scope.handleCertsSelected = function(files, callback) {
          $scope.certsUploading = true;
          $upload.upload({
            url: '/api/v1/superuser/customcerts/' + files[0].name,
            method: 'POST',
            data: {'_csrf_token': window.__token},
            file: files[0]
          }).success(function() {
            callback(true);
            $scope.resetUpload++;
            loadCertificates();
          }).error(function(r) {
            bootbox.alert('Could not upload certificate')
            callback(false);
            $scope.resetUpload++;
            loadCertificates();
          });
        };

        $scope.deleteCert = function(path) {
          var errorDisplay = ApiService.errorDisplay('Could not delete certificate');
          var params = {
            'certpath': path
          };

          ApiService.deleteCustomCertificate(null, params).then(loadCertificates, errorDisplay);
        };
      }
    };
    return directiveDefinitionObject;
  });
