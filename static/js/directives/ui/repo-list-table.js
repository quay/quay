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
      'repoMirroringEnabled': '=repoMirroringEnabled'}, 
    controller: function($scope, $element, $filter, TableService, UserService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.repositories = null;
      $scope.orderedRepositories = [];
      $scope.reposPerPage = 25;

      $scope.maxPopularity = 0;
      $scope.options = {
        'predicate': 'popularity',
        'reverse': false,
        'filter': null,
        'page': 0
      };

      var buildOrderedRepositories = function() {
        if (!$scope.repositories) { return; }

        $scope.orderedRepositories = TableService.buildOrderedItems($scope.repositories,
            $scope.options,
            ['namespace', 'name'], ['last_modified_datetime', 'popularity'])
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