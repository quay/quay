/**
 * An element which displays a link to change a lookup filter, and shows whether it is selected.
 */
angular.module('quay').directive('filterControl', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/filter-control.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'filter': '=filter',
      'value': '@value'
    },
    controller: function($scope, $element) {
      $scope.setFilter = function() {
        $scope.filter = $scope.value;
      };
    }
  };
  return directiveDefinitionObject;
});