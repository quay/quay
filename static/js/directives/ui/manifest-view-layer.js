/**
 * An element which displays a single layer in the manifest view.
 */
angular.module('quay').directive('manifestViewLayer', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/manifest-view-layer.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'manifest': '=manifest',
      'layer': '=layer'
    },
    controller: function($scope, $element) {
      $scope.getClass = function() {
        if ($scope.layer.index == 0) {
          return 'last';
        }

        if ($scope.layer.index == $scope.manifest.layers.length - 1) {
          return 'first';
        }

        return '';
      };
    }
  };
  return directiveDefinitionObject;
});