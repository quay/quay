const templateUrl = require('./registry-name.html');

/**
 * An element which displays the name of the registry (optionally the short name).
 */
angular.module('quay-config').directive('registryName', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl,
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'isShort': '=isShort'
    },
    controller: function($scope, $element) {
      // FIXME: Do we want to encode the name from the context somehow?
      $scope.name = $scope.isShort ? 'Quay' : 'Quay';
    }
  };
  return directiveDefinitionObject;
});

