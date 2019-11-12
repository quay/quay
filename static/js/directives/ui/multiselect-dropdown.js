/**
 * An element which displays a dropdown for selecting multiple elements.
 */
angular.module('quay').directive('multiselectDropdown', function ($compile) {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/multiselect-dropdown.html',
    transclude: true,
    replace: false,
    restrict: 'C',
    scope: {
      'items': '=items',
      'selectedItems': '=selectedItems',
      'itemName': '@itemName',
      'itemChecked': '&itemChecked'
    },
    controller: function($scope, $element) {
      $scope.isChecked = function(checked, item) {
        return checked.indexOf(item) >= 0;
      };

      $scope.toggleItem = function(item) {
        var isChecked = $scope.isChecked($scope.selectedItems, item);
        if (!isChecked) {
          $scope.selectedItems.push(item);
        } else {
          var index = $scope.selectedItems.indexOf(item);
          $scope.selectedItems.splice(index, 1);
        }
        $scope.itemChecked({'item': item, 'checked': !isChecked});
      };
    }
  };
  return directiveDefinitionObject;
});