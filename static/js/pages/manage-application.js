(function() {
  /**
   * Page for managing an organization-defined OAuth application.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('manage-application', 'manage-application.html', ManageApplicationCtrl, {
      'newLayout': true,
      'title': 'Manage Application {{ application.name }}',
      'description': 'Manage an OAuth application'
    });
  }]);

  function ManageApplicationCtrl($scope, $routeParams, $rootScope, $location, $timeout, OAuthService, ApiService, UserService, Config) {
    var orgname = $routeParams.orgname;
    var clientId = $routeParams.clientid;

    $scope.Config = Config;
    $scope.OAuthService = OAuthService;
    $scope.updating = false;

    $scope.genScopes = {};

    UserService.updateUserIn($scope);

    $scope.getScopes = function(scopes) {
      var checked = [];
      for (var scopeName in scopes) {
        if (scopes.hasOwnProperty(scopeName) && scopes[scopeName]) {
          checked.push(scopeName);
        }
      }
      return checked;
    };

    $scope.askResetClientSecret = function() {
      $('#resetSecretModal').modal({});
    };

    $scope.askDelete = function() {
      $('#deleteAppModal').modal({});
    };

    $scope.deleteApplication = function() {
      var params = {
        'orgname': orgname,
        'client_id': clientId
      };

      $('#deleteAppModal').modal('hide');

      ApiService.deleteOrganizationApplication(null, params).then(function(resp) {
        $timeout(function() {
          $location.path('/organization/' + orgname).search('tab', 'applications');
        }, 500);
      }, ApiService.errorDisplay('Could not delete application'));
    };

    $scope.updateApplication = function() {
      $scope.updating = true;
      var params = {
        'orgname': orgname,
        'client_id': clientId
      };

      if (!$scope.application['description']) {
        delete $scope.application['description'];
      }

      if (!$scope.application['avatar_email']) {
        delete $scope.application['avatar_email'];
      }

      var errorHandler = ApiService.errorDisplay('Could not update application', function(resp) {
        $scope.updating = false;
      });

      ApiService.updateOrganizationApplication($scope.application, params).then(function(resp) {
        $scope.application = resp;
      }, errorHandler);
    };

    $scope.resetClientSecret = function() {
      var params = {
        'orgname': orgname,
        'client_id': clientId
      };

      $('#resetSecretModal').modal('hide');

      ApiService.resetOrganizationApplicationClientSecret(null, params).then(function(resp) {
        $scope.application = resp;
      }, ApiService.errorDisplay('Could not reset client secret'));
    };

    var loadOrganization = function() {
      $scope.orgResource = ApiService.getOrganizationAsResource({'orgname': orgname}).get(function(org) {
        $scope.organization = org;
        return org;
      });
    };

    var loadApplicationInfo = function() {
      var params = {
        'orgname': orgname,
        'client_id': clientId
      };

      $scope.appResource = ApiService.getOrganizationApplicationAsResource(params).get(function(resp) {
        $scope.application = resp;

        $rootScope.title = 'Manage Application ' + $scope.application.name  + ' (' + $scope.orgname + ')';
        $rootScope.description = 'Manage the details of application ' + $scope.application.name +
           ' under organization ' + $scope.orgname;

        return resp;
      });
    };


    // Load the organization and application info.
    loadOrganization();
    loadApplicationInfo();
  }
})();