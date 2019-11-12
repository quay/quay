/**
 * An element which displays the phase of a build nicely.
 */
angular.module('quay').directive('buildLogPhase', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-log-phase.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'phase': '=phase'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});
