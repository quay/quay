/**
 * An element which displays a dialog for creating a robot account.
 */
angular.module('quay').directive('createRobotDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/create-robot-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'info': '=info',
      'robotCreated': '&robotCreated'
    },
    controller: function($scope, $element, ApiService, UserService, NAME_PATTERNS) {
      $scope.ROBOT_PATTERN = NAME_PATTERNS.ROBOT_PATTERN;

      $scope.robotFinished = function(robot) {
        $scope.robotCreated({'robot': robot});
      };

      $scope.createRobot = function(name, description, callback) {
        var organization = $scope.info.namespace;
        if (!UserService.isOrganization(organization)) {
          organization = null;
        }

        var params = {
          'robot_shortname': name
        };

        var data = {
          'description': description || ''
        };

        var errorDisplay = ApiService.errorDisplay('Cannot create robot account', function() {
          callback(null);
        });

        ApiService.createRobot(organization, data, params).then(function(resp) {
          callback(resp);
        }, errorDisplay);
      };
    }
  };
  return directiveDefinitionObject;
});