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

  function SuperuserCtrl($scope, $location, ApiService, Features, UserService, ContainerService, $sce,
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
    $scope.disk_size_units = {
      'KB': 1024,
      'MB': 1024**2,
      'GB': 1024**3,
      'TB': 1024**4,
    };
    $scope.quotaUnits = Object.keys($scope.disk_size_units);
    $scope.registryQuota = null;
    $scope.backgroundLoadingOrgs = false;
    $scope.errorLoadingOrgs = false;

    $scope.showQuotaConfig = function (org) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $('#quotaConfigModal-'+org.name).modal('show');
    };

    $scope.bytesToHumanReadableString = function(bytes) {
      let units = Object.keys($scope.disk_size_units).reverse();
      let result = null;
      let byte_unit = null;

      for (const key in units) {
        byte_unit = units[key];
        result = Math.round(bytes / $scope.disk_size_units[byte_unit]);
        if (bytes >= $scope.disk_size_units[byte_unit]) {
          return result.toString() + " " + byte_unit;
        }
      }

      return result.toString() + " " + byte_unit;
    };

    $scope.quotaPercentConsumed = function(organization) {
      if (organization.quota_report && organization.quota_report.configured_quota) {
        return Math.round(organization.quota_report.quota_bytes / organization.quota_report.configured_quota * 100);
      }
      return 0;
    };

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

    var caclulateRegistryStorage = function () {
      if (!Features.QUOTA_MANAGEMENT || !$scope.organizations) {
        return;
      }
      let total = 0;
      $scope.organizations.forEach(function (obj){
        total += obj['quota_report']['quota_bytes'];
      })
      $scope.registryQuota = total;
    }

    $scope.loadOrganizationsInternal = function() {
      $scope.organizations = [];
      if($scope.backgroundLoadingOrgs){
        return;
      }
      loadPaginatedOrganizations();
    };

    var loadPaginatedOrganizations = function(nextPageToken = null) {
      $scope.backgroundLoadingOrgs = true;
      var params = nextPageToken != null ? {limit: 50, next_page: nextPageToken} : {limit: 50};
      ApiService.listAllOrganizationsAsResource(params).get(function(resp) {
        $scope.organizations = [...$scope.organizations, ...resp['organizations']];
        if(resp["next_page"] != null){
          loadPaginatedOrganizations(resp["next_page"]);
        } else {
          $scope.backgroundLoadingOrgs = false;
          caclulateRegistryStorage();
        }
        sortOrgs();
      }, function(resp){
        $scope.errorLoadingOrgs = true;
        $scope.backgroundLoadingOrgs = false;
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
