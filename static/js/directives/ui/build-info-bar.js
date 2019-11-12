/**
 * An element which displays the status of a build in a nice compact bar.
 */
angular.module('quay').directive('buildInfoBar', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-info-bar.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build',
      'showTime': '=showTime',
      'hideId': '=hideId'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});
