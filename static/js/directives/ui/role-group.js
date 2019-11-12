/**
 * An element which displays a set of roles, and highlights the current role. This control also
 * allows the current role to be changed.
 */
angular.module('quay').directive('roleGroup', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/role-group.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'roles': '@roles',
      'currentRole': '=currentRole',
      'readOnly': '=readOnly',
      'roleChanged': '&roleChanged',
      'pullLeft': '@pullLeft'
    },
    controller: function($scope, $element, RolesService, Config) {
      $scope.fullRoles = RolesService[$scope.roles];
      $scope.Config = Config;

      $scope.setRole = function(role) {
        if ($scope.currentRole == role) { return; }
        if ($scope.roleChanged) {
          $scope.roleChanged({'role': role});
        } else {
          $scope.currentRole = role;
        }
      };

      $scope.getRoleInfo = function(role) {
        var found = null;
        $scope.fullRoles.forEach(function(r) {
          if (r.id == role) { found = r; }
        });
        return found;
      };
    }
  };
  return directiveDefinitionObject;
});