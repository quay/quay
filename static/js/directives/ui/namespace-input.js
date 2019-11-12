/**
 * An element which displays an input box for creating a namespace.
 */
angular.module('quay').directive('namespaceInput', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/namespace-input.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'binding': '=binding',
      'backIncompatMessage': '=backIncompatMessage',
      'hasExternalError': '=?hasExternalError',

      'namespaceTitle': '@namespaceTitle',
    },
    controller: function($scope, $element, NAME_PATTERNS) {
      $scope.USERNAME_PATTERN = NAME_PATTERNS.USERNAME_PATTERN;
      $scope.usernamePattern = new RegExp(NAME_PATTERNS.USERNAME_PATTERN);

      $scope.$watch('binding', function(binding) {
        if (!binding) {
          $scope.backIncompatMessage = null;
          return;
        }

        if (binding.indexOf('-') > 0 || binding.indexOf('.') > 0) {
          $scope.backIncompatMessage = 'Namespaces with dashes or dots are only compatible with Docker 1.9+';
        } else if (binding.length < 4 || binding.length > 30) {
          $scope.backIncompatMessage = 'Namespaces less than 4 or more than 30 characters are only compatible with Docker 1.6+';
        } else {
          $scope.backIncompatMessage = null;
        }
      })
    }
  };
  return directiveDefinitionObject;
});