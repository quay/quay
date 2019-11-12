/**
 * An element which displays a user-friendly message for the current phase of a build.
 */
angular.module('quay').directive('buildMessage', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-message.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'phase': '=phase'
    },
    controller: function($scope, $element, BuildService) {
      $scope.getBuildMessage = function (phase) {
        return BuildService.getBuildMessage(phase);
      };
    }
  };
  return directiveDefinitionObject;
});
