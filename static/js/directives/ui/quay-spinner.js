/**
 * A spinner.
 */
angular.module('quay').directive('quaySpinner', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/spinner.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {},
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});
