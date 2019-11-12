(function() {
  /**
   * The superuser admin page provides a new management UI for Red Hat Quay.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('superuser', 'super-user.html', SuperuserCtrl,
      {
        'newLayout': true,
        'title': 'Red Hat Quay Management'
      })
  }]);

  function SuperuserCtrl($scope, $location, ApiService, Features, UserService, ContainerService,
                         AngularPollChannel, CoreDialog, TableService, StateService) {
    if (!Features.SUPER_USERS) {
      return;
    }

    $scope.inReadOnlyMode = StateService.inReadOnlyMode();

    // Monitor any user changes and place the current user into the scope.
    UserService.updateUserIn($scope);

    $scope.configStatus = null;
    $scope.logsCounter = 0;
    $scope.changeLog = null;
    $scope.logsInstance = null;
    $scope.pollChannel = null;
    $scope.logsScrolled = false;
    $scope.csrf_token = encodeURIComponent(window.__token);
    $scope.currentConfig = null;
    $scope.serviceKeysActive = false;
    $scope.globalMessagesActive = false;
    $scope.superUserBuildLogsActive = false;
    $scope.manageUsersActive = false;
    $scope.orderedOrgs = [];
    $scope.orgsPerPage = 10;
    $scope.options = {
      'predicate': 'name',
      'reverse': false,
      'filter': null,
      'page': 0,
    }

    $scope.loadMessageOfTheDay = function () {
      $scope.globalMessagesActive = true;
    };

    $scope.loadSuperUserBuildLogs = function () {
      $scope.superUserBuildLogsActive = true;
    };

    $scope.loadServiceKeys = function() {
      $scope.serviceKeysActive = true;
    };

    $scope.getChangeLog = function() {
      if ($scope.changeLog) { return; }

      ApiService.getChangeLog().then(function(resp) {
        $scope.changeLog = resp;
      }, ApiService.errorDisplay('Cannot load change log. Please contact support.'))
    };

    $scope.loadUsageLogs = function() {
      $scope.logsCounter++;
    };

    $scope.loadOrganizations = function() {
      if ($scope.organizations) {
        return;
      }

      $scope.loadOrganizationsInternal();
    };

    var sortOrgs = function() {
      if (!$scope.organizations) {return;}
      $scope.orderedOrgs = TableService.buildOrderedItems($scope.organizations, $scope.options,
                                                           ['name', 'email'], []);
      };

    $scope.loadOrganizationsInternal = function() {
      $scope.organizationsResource = ApiService.listAllOrganizationsAsResource().get(function(resp) {
        $scope.organizations = resp['organizations'];
        sortOrgs();
        return $scope.organizations;
      });
    };

    $scope.loadUsers = function() {
      $scope.manageUsersActive = true;
    };

    $scope.tablePredicateClass = function(name, predicate, reverse) {
      if (name != predicate) {
        return '';
      }
      return 'current ' + (reverse ? 'reversed' : '');
    };

    $scope.orderBy = function(predicate) {
      if (predicate == $scope.options.predicate) {
        $scope.options.reverse = !$scope.options.reverse;
        return;
      }
      $scope.options.reverse = false;
      $scope.options.predicate = predicate;
    };
    $scope.askDeleteOrganization = function(org) {
      bootbox.confirm('Are you sure you want to delete this organization? Its data will be deleted with it.',
        function(result) {
          if (!result) { return; }

          var params = {
            'name': org.name
          };

          ApiService.deleteOrganization(null, params).then(function(resp) {
            $scope.loadOrganizationsInternal();
          }, ApiService.errorDisplay('Could not delete organization'));
        });
    };

    $scope.askRenameOrganization = function(org) {
      bootbox.prompt('Enter a new name for the organization:', function(newName) {
        if (!newName) { return; }

        var params = {
          'name': org.name
        };

        var data = {
          'name': newName
        };

        ApiService.changeOrganization(data, params).then(function(resp) {
          $scope.loadOrganizationsInternal();
          org.name = newName;
        }, ApiService.errorDisplay('Could not rename organization'));
      });
    };

    $scope.askTakeOwnership = function (entity) {
      $scope.takeOwnershipInfo = {
        'entity': entity
      };
    };

    $scope.takeOwnership = function (info, callback) {
      var errorDisplay = ApiService.errorDisplay('Could not take ownership of namespace', callback);
      var params = {
        'namespace': info.entity.username || info.entity.name
      };

      ApiService.takeOwnership(null, params).then(function () {
        callback(true);
        $location.path('/organization/' + params.namespace);
      }, errorDisplay)
    };

    $scope.checkStatus = function() {
      ContainerService.checkStatus(function(resp) {
        $('#restartingContainerModal').modal('hide');
        $scope.configStatus = resp['status'];
        $scope.configProviderId = resp['provider_id'];

        if ($scope.configStatus == 'ready') {
          $scope.currentConfig = null;
          $scope.loadUsers();
        } else {
          var message = "Installation of this product has not yet been completed." +
                        "<br><br>Please read the " +
                        "<a href='https://coreos.com/docs/enterprise-registry/initial-setup/'>" +
                        "Setup Guide</a>";

          var title = "Installation Incomplete";
          CoreDialog.fatal(title, message);
        }
      }, $scope.currentConfig);
    };

    // Load the initial status.
    $scope.checkStatus();
    $scope.$watch('options.predicate', sortOrgs);
    $scope.$watch('options.reverse', sortOrgs);
    $scope.$watch('options.filter', sortOrgs);

  }
}());
