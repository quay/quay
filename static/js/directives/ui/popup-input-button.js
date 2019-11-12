/**
 * An element which, when clicked, displays a popup input dialog to accept a text value.
 */
angular.module('quay').directive('popupInputButton', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/popup-input-button.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'placeholder': '=placeholder',
      'pattern': '=pattern',
      'submitted': '&submitted'
    },
    controller: function($scope, $element) {
      $scope.patternMap = {};

      $scope.popupShown = function() {
        setTimeout(function() {
          var box = $('#input-box');
          box[0].value = '';
          box.focus();
        }, 40);
      };

      $scope.getRegexp = function(pattern) {
        if (!pattern) {
          pattern = '.*';
        }

        if ($scope.patternMap[pattern]) {
          return $scope.patternMap[pattern];
        }

        return $scope.patternMap[pattern] = new RegExp(pattern);
      };

      $scope.inputSubmit = function() {
        var box = $('#input-box');
        if (box.hasClass('ng-invalid')) { return; }

        var entered = box[0].value;
        if (!entered) {
          return;
        }

        if ($scope.submitted) {
          $scope.submitted({'value': entered});
        }
      };
    }
  };
  return directiveDefinitionObject;
});