/**
 * An element which displays the header bar for a manager UI component.
 */
angular.module('quay').directive('managerHeader', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/manager-header.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'headerTitle': '@headerTitle'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});