/**
 * An element which displays either a resource (if present) or an error message if the resource
 * failed to load.
 */
angular.module('quay').directive('resourceView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/resource-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'resource': '=resource',
      'resources': '=resources',
      'errorMessage': '=errorMessage'
    },
    controller: function($scope, $element) {
      $scope.getState = function() {
        if (!$scope.resources && !$scope.resource) {
          return 'loading';
        }

        var resources = $scope.resources || [$scope.resource];
        if (!resources.length) {
          return 'loading';
        }

        for (var i = 0; i < resources.length; ++i) {
          var current = resources[i];
          if (current.loading) {
            return 'loading';
          }

          if (current.hasError) {
            return 'error';
          }
        }

        return 'ready';
      };
    }
  };
  return directiveDefinitionObject;
});