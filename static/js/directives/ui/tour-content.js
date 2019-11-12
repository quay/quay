/**
 * An element which implements a frame for content in the application tour, making sure to
 * chromify any marked elements found. Note that this directive relies on the browserchrome library
 * in the lib/ folder.
 */
angular.module('quay').directive('tourContent', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/tour-content.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'kind': '=kind'
    },
    controller: function($scope, $element, $timeout, UserService) {
      // Monitor any user changes and place the current user into the scope.
      UserService.updateUserIn($scope);

      $scope.chromify = function() {
        browserchrome.update();
      };

      $scope.$watch('kind', function(kind) {
        $timeout(function() {
          $scope.chromify();
        });
      });
    },
    link: function($scope, $element, $attr, ctrl) {
      $scope.chromify();
    }
  };
  return directiveDefinitionObject;
});
