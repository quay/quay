/**
 * An element which displays the status of a build as a mini-bar.
 */
angular.module('quay').directive('buildMiniStatus', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-mini-status.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build',
      'canView': '=canView'
    },
    controller: function($scope, $element, BuildService) {
      $scope.isBuilding = function(build) {
        if (!build) { return true; }
        return BuildService.isActive(build)
      };
    }
  };
  return directiveDefinitionObject;
});