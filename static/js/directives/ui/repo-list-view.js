/**
 * An element that displays a list (grid or table) of repositories.
 */
angular.module('quay').directive('repoListView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-list-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      namespaces: '=namespaces',
      starredRepositories: '=starredRepositories',
      starToggled: '&starToggled',
      repoKind: '@repoKind',
      repoMirroringEnabled: '=repoMirroringEnabled'
    },
    controller: function($scope, $element, CookieService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.resources = [];
      $scope.loading = true;
      $scope.optionAllowed = true;

      $scope.$watch('namespaces', function(namespaces) {
        if (!namespaces) { return; }

        $scope.loading = false;
        $scope.resources = [];
        namespaces.forEach(function(namespace) {
          if (namespace && namespace.repositories) {
            $scope.resources.push(namespace.repositories);
            if (namespace.repositories.loading) {
              $scope.loading = true;
            }
          }
        });
      }, true);
    }
  };
  return directiveDefinitionObject;
});