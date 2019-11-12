(function() {
  /**
   * The Incomplete Setup page provides information to the user about what's wrong with the current configuration
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('incomplete-setup', 'incomplete-setup.html', IncompleteSetupCtrl,
      {
        'newLayout': true,
        'title': 'Red Hat Quay Setup Incomplete'
      })
  }]);

  function IncompleteSetupCtrl($scope, $location, $timeout, ApiService, Features, UserService, ContainerService, CoreDialog, Config) {
    if (Config['SETUP_COMPLETE']) {
      $location.path('/');
      return;
    }
    if (!Features.SUPER_USERS) {
      return;
    }

    $scope.States = {
      // Loading the state of the product.
      'LOADING': 'loading',

      // The configuration directory is missing.
      'MISSING_CONFIG_DIR': 'missing-config-dir',

      // The config.yaml exists but it is invalid.
      'INVALID_CONFIG': 'config-invalid',
    };

    $scope.currentStep = $scope.States.LOADING;

    $scope.$watch('currentStep', function(currentStep) {
      switch (currentStep) {
        case $scope.States.MISSING_CONFIG_DIR:
          $scope.showMissingConfigDialog();
          break;

        case $scope.States.INVALID_CONFIG:
          $scope.showInvalidConfigDialog();
            break;
      }
    });

    $scope.showInvalidConfigDialog = function() {
      var message = "The <code>config.yaml</code> file found in <code>conf/stack</code> could not be parsed."
      var title = "Invalid configuration file";
      CoreDialog.fatal(title, message);
    };


    $scope.showMissingConfigDialog = function() {
      var title = "Missing configuration volume";
      var message = "It looks like Quay was not mounted with a configuration volume. The volume should be " +
                    "mounted into the container at <code>/conf/stack</code>. " +
                    "<br>If you have a tarball, please ensure you untar it into a directory and re-run this container with: " +
                    "<br><br><pre>docker run -v /path/to/config:/conf/stack</pre>" +
                    "<br>If you haven't configured your Quay instance, please run the container with: " +
                    "<br><br><pre>docker run &lt;name-of-image&gt; config </pre>" +
                    "For more information, " +
                    "<a href='https://coreos.com/docs/enterprise-registry/initial-setup/'>" +
                    "Read the Setup Guide</a>";

      if (window.__kubernetes_namespace) {
        title = "Configuration Secret Missing";
        message = `It looks like the Red Hat Quay secret is not present in the namespace <code>${window.__kubernetes_namespace}.</code>` +
                  "<br>Please double-check that the secret exists, or " +
                  "<a href='https://coreos.com/docs/enterprise-registry/initial-setup/'>" +
                  "refer to the Setup Guide</a>";
      }

      CoreDialog.fatal(title, message);
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