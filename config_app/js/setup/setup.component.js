import * as URI from 'urijs';
const templateUrl = require('./setup.html');

(function() {
    /**
     * The Setup page provides a nice GUI walkthrough experience for setting up Red Hat Quay.
     */

    angular.module('quay-config').directive('setup', () => {
      const directiveDefinitionObject = {
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
        controller: SetupCtrl,
      };

      return directiveDefinitionObject;
    })

    function SetupCtrl($scope, $timeout, ApiService, Features,  UserService, ContainerService, CoreDialog) {
        // if (!Features.SUPER_USERS) {
        //     return;
        // }

        $scope.HOSTNAME_REGEX = '^[a-zA-Z-0-9_\.\-]+(:[0-9]+)?$';

        $scope.validateHostname = function(hostname) {
            if (hostname.indexOf('127.0.0.1') == 0 || hostname.indexOf('localhost') == 0) {
                return 'Please specify a non-localhost hostname. "localhost" will refer to the container, not your machine.'
            }

            return null;
        };

        // Note: The values of the enumeration are important for isStepFamily. For example,
        // *all* states under the "configuring db" family must start with "config-db".
        $scope.States = {
            // Loading the state of the product.
            'LOADING': 'loading',

            // The configuration directory is missing.
            'MISSING_CONFIG_DIR': 'missing-config-dir',

            // The config.yaml exists but it is invalid.
            'INVALID_CONFIG': 'config-invalid',

            // DB is being configured.
            'CONFIG_DB': 'config-db',

            // DB information is being validated.
            'VALIDATING_DB': 'config-db-validating',

            // DB information is being saved to the config.
            'SAVING_DB': 'config-db-saving',

            // A validation error occurred with the database.
            'DB_ERROR': 'config-db-error',

            // Database is being setup.
            'DB_SETUP': 'setup-db',

            // An error occurred when setting up the database.
            'DB_SETUP_ERROR': 'setup-db-error',

            // A superuser is being configured.
            'CREATE_SUPERUSER': 'create-superuser',

            // The superuser is being created.
            'CREATING_SUPERUSER': 'create-superuser-creating',

            // An error occurred when setting up the superuser.
            'SUPERUSER_ERROR': 'create-superuser-error',

            // The superuser was created successfully.
            'SUPERUSER_CREATED': 'create-superuser-created',

            // General configuration is being setup.
            'CONFIG': 'config',

            // The configuration is fully valid.
            'VALID_CONFIG': 'valid-config',

            // The product is ready for use.
            'READY': 'ready'
        }

        $scope.csrf_token = window.__token;
        $scope.currentStep = $scope.States.LOADING;
        $scope.errors = {};
        $scope.stepProgress = [];
        $scope.hasSSL = false;
        $scope.hostname = null;
        $scope.currentConfig = null;

        $scope.currentState = {
            'hasDatabaseSSLCert': false
        };

        $scope.$watch('currentStep', function(currentStep) {
            $scope.stepProgress = $scope.getProgress(currentStep);

            switch (currentStep) {
                case $scope.States.CONFIG:
                    $('#setupModal').modal('hide');
                    break;

                case $scope.States.MISSING_CONFIG_DIR:
                    $scope.showMissingConfigDialog();
                    break;

                case $scope.States.INVALID_CONFIG:
                    $scope.showInvalidConfigDialog();
                    break;

                case $scope.States.DB_SETUP:
                    $scope.performDatabaseSetup();
                // Fall-through.

                case $scope.States.CREATE_SUPERUSER:
                case $scope.States.CONFIG_DB:
                case $scope.States.VALID_CONFIG:
                case $scope.States.READY:
                    $('#setupModal').modal({
                        keyboard: false,
                        backdrop: 'static'
                    });
                    break;
            }
        });

        $scope.restartContainer = function(state) {
            $scope.currentStep = state;
            ContainerService.restartContainer(function() {
                $scope.checkStatus()
            });
        };

        $scope.showSuperuserPanel = function() {
            $('#setupModal').modal('hide');
            var prefix = $scope.hasSSL ? 'https' : 'http';
            var hostname = $scope.hostname;
            if (!hostname) {
                hostname = document.location.hostname;
                if (document.location.port) {
                    hostname = hostname + ':' + document.location.port;
                }
            }

            window.location = prefix + '://' + hostname + '/superuser';
        };

        $scope.configurationSaved = function(config) {
            $scope.hasSSL = config['PREFERRED_URL_SCHEME'] == 'https';
            $scope.hostname = config['SERVER_HOSTNAME'];
            $scope.currentConfig = config;

            $scope.currentStep = $scope.States.VALID_CONFIG;
        };

        $scope.getProgress = function(step) {
            var isStep = $scope.isStep;
            var isStepFamily = $scope.isStepFamily;
            var States = $scope.States;

            return [
                isStepFamily(step, States.CONFIG_DB),
                isStepFamily(step, States.DB_SETUP),
                isStepFamily(step, States.CREATE_SUPERUSER),
                isStep(step, States.CONFIG),
                isStep(step, States.VALID_CONFIG),
                isStep(step, States.READY)
            ];
        };

        $scope.isStepFamily = function(step, family) {
            if (!step) { return false; }
            return step.indexOf(family) == 0;
        };

        $scope.isStep = function(step) {
            for (var i = 1; i < arguments.length; ++i) {
                if (arguments[i] == step) {
                    return true;
                }
            }
            return false;
        };

        $scope.beginSetup = function() {
            $scope.currentStep = $scope.States.CONFIG_DB;
        };

        $scope.showInvalidConfigDialog = function() {
            var message = "The <code>config.yaml</code> file found in <code>conf/stack</code> could not be parsed."
            var title = "Invalid configuration file";
            CoreDialog.fatal(title, message);
        };


        $scope.showMissingConfigDialog = function() {
            var message = "A volume should be mounted into the container at <code>/conf/stack</code>: " +
                "<br><br><pre>docker run -v /path/to/config:/conf/stack</pre>" +
                "<br>Once fixed, restart the container. For more information, " +
                "<a href='https://coreos.com/docs/enterprise-registry/initial-setup/'>" +
                "Read the Setup Guide</a>"

            var title = "Missing configuration volume";
            CoreDialog.fatal(title, message);
        };

        $scope.parseDbUri = function(value) {
            if (!value) { return null; }

            // Format: mysql+pymysql://<username>:<url escaped password>@<hostname>/<database_name>
            var uri = URI(value);
            return {
                'kind': uri.protocol(),
                'username': uri.username(),
                'password': uri.password(),
                'server': uri.host(),
                'database': uri.path() ? uri.path().substr(1) : ''
            };
        };

        $scope.serializeDbUri = function(fields) {
            if (!fields['server']) { return ''; }
            if (!fields['database']) { return ''; }

            var uri = URI();
            try {
                uri = uri && uri.host(fields['server']);
                uri = uri && uri.protocol(fields['kind']);
                uri = uri && uri.username(fields['username']);
                uri = uri && uri.password(fields['password']);
                uri = uri && uri.path('/' + (fields['database'] || ''));
                uri = uri && uri.toString();
            } catch (ex) {
                return '';
            }

            return uri;
        };

        $scope.createSuperUser = function() {
            $scope.currentStep = $scope.States.CREATING_SUPERUSER;
            ApiService.scCreateInitialSuperuser($scope.superUser, null).then(function(resp) {
                $scope.checkStatus();
            }, function(resp) {
                $scope.currentStep = $scope.States.SUPERUSER_ERROR;
                $scope.errors.SuperuserCreationError = ApiService.getErrorMessage(resp, 'Could not create superuser');
            });
        };

        $scope.performDatabaseSetup = function() {
            $scope.currentStep = $scope.States.DB_SETUP;
            ApiService.scSetupDatabase(null, null).then(function(resp) {
                if (resp['error']) {
                    $scope.currentStep = $scope.States.DB_SETUP_ERROR;
                    $scope.errors.DatabaseSetupError = resp['error'];
                } else {
                    $scope.currentStep = $scope.States.CREATE_SUPERUSER;
                }
            }, ApiService.errorDisplay('Could not setup database. Please report this to support.'))
        };

        $scope.validateDatabase = function() {
            $scope.currentStep = $scope.States.VALIDATING_DB;
            $scope.databaseInvalid = null;

            var data = {
                'config': {
                    'DB_URI': $scope.databaseUri
                },
            };

            if ($scope.currentState.hasDatabaseSSLCert) {
                data['config']['DB_CONNECTION_ARGS'] = {
                    'ssl': {
                        'ca': 'conf/stack/database.pem'
                    }
                };
            }

            var params = {
                'service': 'database'
            };

            ApiService.scValidateConfig(data, params).then(function(resp) {
                var status = resp.status;

                if (status) {
                    $scope.currentStep = $scope.States.SAVING_DB;
                    ApiService.scUpdateConfig(data, null).then(function(resp) {
                        $scope.checkStatus();
                    }, ApiService.errorDisplay('Cannot update config. Please report this to support'));
                } else {
                    $scope.currentStep = $scope.States.DB_ERROR;
                    $scope.errors.DatabaseValidationError = resp.reason;
                }
            }, ApiService.errorDisplay('Cannot validate database. Please report this to support'));
        };

        $scope.checkStatus = function() {
            ContainerService.checkStatus(function(resp) {
                $scope.currentStep = resp['status'];
            }, $scope.currentConfig);
        };

        // Load the initial status.
        $scope.checkStatus();
    };
})();
