/**
 * An element which displays the name of the registry (optionally the short name).
 */
angular.module('quay').directive('registryName', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/registry-name.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'isShort': '=isShort'
    },
    controller: function($scope, $element, Config) {
      $scope.name = $scope.isShort ? Config.REGISTRY_TITLE_SHORT : Config.REGISTRY_TITLE;
    }
  };
  return directiveDefinitionObject;
});

