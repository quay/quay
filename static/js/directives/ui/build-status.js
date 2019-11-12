/**
 * DEPRECATED: An element which displays the status of a build.
 */
angular.module('quay').directive('buildStatus', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-status.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});