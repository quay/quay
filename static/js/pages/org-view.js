(function() {
  /**
   * Page that displays details about an organization, such as its teams.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('org-view', 'org-view.html', OrgViewCtrl, {
      'newLayout': true,
      'title': 'Organization {{ organization.name }}',
      'description': 'Organization {{ organization.name }}'
    })
  }]);

  function OrgViewCtrl($scope, $routeParams, $timeout, ApiService, UIService, AvatarService,
                       Config, Features, StateService) {
    var orgname = $routeParams.orgname;

    $scope.inReadOnlyMode = StateService.inReadOnlyMode();
    $scope.namespace = orgname;
    $scope.showLogsCounter = 0;
    $scope.showApplicationsCounter = 0;
    $scope.showBillingCounter = 0;
    $scope.showRobotsCounter = 0;
    $scope.showTeamsCounter = 0;
    $scope.changeEmailInfo = null;
    $scope.context = {};

    $scope.Config = Config;
    $scope.Features = Features;

    $scope.orgScope = {
      'changingOrganization': false,
      'organizationEmail': ''
    };

    $scope.$watch('orgScope.organizationEmail', function(e) {
      UIService.hidePopover('#changeEmailForm input');
    });

    var loadRepositories = function() {
      var options = {
        'namespace': orgname,
        'public': true,
        'last_modified': true,
        'popularity': true
      };

      $scope.organization.repositories = ApiService.listReposAsResource().withPagination('repositories').withOptions(options).get(function(resp) {
        return resp.repositories;
      });
    };

    var loadOrganization = function() {
      $scope.orgResource = ApiService.getOrganizationAsResource({'orgname': orgname}).get(function(org) {
        $scope.organization = org;
        $scope.orgScope.organizationEmail = org.email;
        $scope.isAdmin = org.is_admin;
        $scope.isMember = org.is_member;

        // Load the repositories.
        $timeout(function() {
          loadRepositories();
        }, 10);
      });
    };

    // Load the organization.
    loadOrganization();

    $scope.showRobots = function() {
      $scope.showRobotsCounter++;
    };

    $scope.showTeams = function() {
      $scope.showTeamsCounter++;
    };

    $scope.showBilling = function() {
      $scope.showBillingCounter = true;
    };

    $scope.showApplications = function() {
      $scope.showApplicationsCounter++;
    };

    $scope.showLogs = function() {
      $scope.showLogsCounter++;
    };

    $scope.showChangeEmail = function() {
      $scope.changeEmailInfo = {
        'email': $scope.organization.email
      };
    };

    $scope.changeEmail = function(info, callback) {
      var params = {
        'orgname': orgname
      };

      var details = {
        'email': $scope.changeEmailInfo.email
      };

      var errorDisplay = ApiService.errorDisplay('Could not change email address', callback);

      ApiService.changeOrganizationDetails(details, params).then(function() {
        $scope.organization.email = $scope.changeEmailInfo.email;
        callback(true);
      }, errorDisplay);
    };
  }
})();