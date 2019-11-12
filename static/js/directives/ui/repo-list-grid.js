/**
 * An element that displays a list of repositories in a grid.
 */
angular.module('quay').directive('repoListGrid', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-list-grid.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      repositoriesResource: '=repositoriesResource',
      starred: '=starred',
      namespace: '=namespace',
      starToggled: '&starToggled',
      hideTitle: '=hideTitle',
      hideNamespaces: '=hideNamespaces',
      repoKind: '@repoKind'
    },
    controller: function($scope, $element, UserService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.isOrganization = function(namespace) {
        return !!UserService.getOrganization(namespace);
      };
    }
  };
  return directiveDefinitionObject;
});