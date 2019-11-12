/**
 * An element which displays an icon representing the state of the build.
 */
angular.module('quay').directive('buildStateIcon', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-state-icon.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build'
    },
    controller: function($scope, $element, BuildService) {
      $scope.isBuilding = function(build) {
        if (!build) { return true; }
        return BuildService.isActive(build);
      };
    }
  };
  return directiveDefinitionObject;
});