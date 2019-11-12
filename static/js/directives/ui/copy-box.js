/**
 * An element which displays a textfield with a "Copy to Clipboard" icon next to it.
 */
angular.module('quay').directive('copyBox', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/copy-box.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'value': '=value',
    },
    controller: function($scope, $element, $rootScope) {
      $scope.disabled = false;

      var number = $rootScope.__copyBoxIdCounter || 0;
      $rootScope.__copyBoxIdCounter = number + 1;
      $scope.inputId = "copy-box-input-" + number;
    }
  };
  return directiveDefinitionObject;
});
