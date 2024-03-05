/**
 * An element which displays a table of repositories.
 */
angular.module('quay').directive('repoListTable', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-list-table.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repositoriesResources': '=repositoriesResources',
      'namespaces': '=namespaces',
      'starToggled': '&starToggled',
      'repoKind': '@repoKind',
      'repoMirroringEnabled': '=repoMirroringEnabled'
    },
    controller: function($scope, $element, $filter, TableService, UserService, StateService, Config) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.repositories = null;
      $scope.orderedRepositories = [];
      $scope.reposPerPage = 25;
      $scope.quotaManagementEnabled = Config.FEATURE_QUOTA_MANAGEMENT && Config.FEATURE_EDIT_QUOTA;
      $scope.repoMirroringEnabled = Config.FEATURE_REPO_MIRROR;
      $scope.maxPopularity = 0;
      $scope.options = {
        'predicate': 'popularity',
        'reverse': false,
        'filter': null,
        'page': 0
      };
      $scope.disk_size_units = {
        'KiB': 1024,
        'MiB': 1024**2,
        'GiB': 1024**3,
        'TiB': 1024**4,
      };
      $scope.quotaUnits = Object.keys($scope.disk_size_units);

      var buildOrderedRepositories = function() {
        if (!$scope.repositories) { return; }

        $scope.orderedRepositories = TableService.buildOrderedItems($scope.repositories,
            $scope.options,
            ['namespace', 'name', 'state'], ['last_modified_datetime', 'popularity', 'quota_report'])
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

      $scope.bytesToHumanReadableString = function(bytes) {
        let units = Object.keys($scope.disk_size_units).reverse();
        let result = null;
        let byte_unit = null;
        for (const key in units) {
          byte_unit = units[key];
          result = (bytes / $scope.disk_size_units[byte_unit]).toFixed(2);
          if (bytes >= $scope.disk_size_units[byte_unit]) {
            return result.toString() + " " + byte_unit;
          }
        }

        return result.toString() + " " + byte_unit;
      };

      $scope.quotaPercentConsumed = function(repository) {
	      if (repository.quota_report && repository.quota_report.configured_quota) {
	        return Math.round(repository.quota_report.quota_bytes / repository.quota_report.configured_quota * 100);
	      }
	      return 0;
      };

      $scope.getAvatarData = function(namespace) {
        var found = {};
        $scope.namespaces.forEach(function(current) {
          if (current.name == namespace || current.username == namespace) {
            found = current.avatar;
          }
        });
        return found;
      };

      $scope.getStrengthClass = function(value, max, id) {
        var adjusted = Math.round((value / max) * 5);
        if (adjusted >= id) {
          return 'active-' + adjusted;
        }

        return '';
      };

      $scope.$watch('options.predicate', buildOrderedRepositories);
      $scope.$watch('options.reverse', buildOrderedRepositories);
      $scope.$watch('options.filter', buildOrderedRepositories);

      $scope.$watch('repositoriesResources', function(resources) {
        $scope.repositories = [];
        $scope.maxPopularity = 0;
        $scope.isLoading = false;

        resources.forEach(function(resource) {
          if (resource.loading) {
            $scope.isLoading = true;
          }

          (resource.value || []).forEach(function(repository) {
            var repositoryInfo = $.extend(repository, {
              'full_name': repository.namespace + '/' + repository.name,
              'last_modified_datetime': TableService.getReversedTimestamp(repository.last_modified),
            });

            $scope.repositories.push(repositoryInfo);
            $scope.maxPopularity = Math.max($scope.maxPopularity, repository.popularity);
          });
        });

        buildOrderedRepositories();

        $scope.loggedIn = !UserService.currentUser().anonymous;
      }, /* deep */ true);
    }
  };
  return directiveDefinitionObject;
});
