/**
 * An element which displays a settings table row for deleting a namespace (user or organization).
 */
angular.module('quay').directive('deleteNamespaceView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/delete-namespace-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'user': '=user',
      'organization': '=organization',
      'subscriptionStatus': '=subscriptionStatus',
      'namespaceTitle': '@namespaceTitle'
    },
    controller: function($scope, $element, UserService) {
      $scope.context = {};

      $scope.showDeleteNamespace = function() {
        $scope.deleteNamespaceInfo = {
          'user': $scope.user,
          'organization': $scope.organization,
          'namespace': $scope.user ? $scope.user.username : $scope.organization.name,
          'verification': ''
        };
      };

      $scope.deleteNamespace = function(info, callback) {
        UserService.deleteNamespace(info, callback);
      };
    }
  };
  return directiveDefinitionObject;
});