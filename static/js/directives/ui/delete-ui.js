/**
 * A two-step delete button that slides into view when clicked.
 */
angular.module('quay').directive('deleteUi', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/delete-ui.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'deleteTitle': '=deleteTitle',
      'buttonTitle': '=buttonTitle',
      'performDelete': '&performDelete'
    },
    controller: function($scope, $element) {
      $scope.buttonTitleInternal = $scope.buttonTitle || 'Delete';

      $element.children().attr('tabindex', 0);
      $scope.focus = function() {
        $element[0].firstChild.focus();
      };
    }
  };
  return  directiveDefinitionObject;
});