/**
 * An element which displays a right-aligned control bar with an <input> for filtering a collection.
 */
angular.module('quay').directive('filterBox', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/filter-box.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'collection': '=collection',
      'filterModel': '=filterModel',
      'filterName': '@filterName'
    },
    controller: function($scope, $element) {

    }
  };
  return directiveDefinitionObject;
});