/**
 * An element which displays the strength of a value (like a signal indicator on a cell phone).
 */
angular.module('quay').directive('strengthIndicator', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/strength-indicator.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'value': '=value',
      'maximum': '=maximum',
      'logBase': '=logBase'
    },
    controller: function($scope, $element) {
      $scope.strengthClass = '';

      var calculateClass = function() {
        if ($scope.value == null || $scope.maximum == null) {
          $scope.strengthClass = '';
          return;
        }

        var value = Math.round(($scope.value / $scope.maximum) * 4);
        if ($scope.logBase) {
          var currentValue = Math.log($scope.value) / Math.log($scope.logBase * 1);
          var maximum = Math.log($scope.maximum) / Math.log($scope.logBase * 1);
          value = Math.round((currentValue / maximum) * 4);
        }

        if (value <= 0) {
          $scope.strengthClass = 'none';
          return;
        }

        if (value <= 1) {
          $scope.strengthClass = 'poor';
          return;
        }

        if (value <= 2) {
          $scope.strengthClass = 'barely';
          return;
        }

        if (value <= 3) {
          $scope.strengthClass = 'fair';
          return;
        }

        $scope.strengthClass = 'good';
      };

      $scope.$watch('maximum', calculateClass);
      $scope.$watch('value', calculateClass);
    }
  };
  return directiveDefinitionObject;
});