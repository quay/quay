/**
 * An element which displays a dialog for setting permissions for an entity to repositories under
 * a namespace.
 */
angular.module('quay').directive('setRepoPermissionsDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/set-repo-permissions-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'info': '=info',

      'permissionsSet': '&permissionsSet',
    },

    controller: function($scope, $element) {
      $scope.setPermissionsCounter = 0;
      $scope.loading = false;
      $scope.context = {};

      $scope.setPermissions = function() {
        $scope.setPermissionsCounter++;
      };

      $scope.settingPermissions = function() {
        $scope.working = true;
      };

      $scope.show = function() {
        $scope.setPermissionsCounter = 0;
        $scope.working = false;
        $element.find('.modal').modal({});
      };

      $scope.hide = function() {
        $scope.working = false;
        $scope.context.info = null;
        $scope.context.hasChangedRepositories = false;
        $scope.context.hasCheckedRepositories = false;

        $element.find('.modal').modal('hide');
      };

      $scope.permissionsSetComplete = function(repositories) {
        $scope.hide();
        $scope.permissionsSet({'repositories': repositories, 'info': $scope.info});
      };

      $scope.$watch('info', function(info) {
        if (info) {
          $scope.context.info = info;
          $scope.show();
        }
      });
    }
  };
  return directiveDefinitionObject;
});