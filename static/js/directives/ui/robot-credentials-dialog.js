/**
 * An element which displays a robot credentials dialog.
 */
angular.module('quay').directive('robotCredentialsDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/robot-credentials-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'info': '=info',
    },
    controller: function($scope, $element, ApiService, UserService, StateService) {
      $scope.credentials = null;
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();

      var lookupRobot = function() {
        var pieces = $scope.info.name.split('+');
        var params = {
          'robot_shortname': pieces[1]
        };

        $scope.credentials = {
          'loading': true
        };

        var organization = UserService.isOrganization(pieces[0]) ? pieces[0] : null;
        ApiService.getRobot(organization, null, params).then(function(resp) {
          $scope.credentials = {
            'username': $scope.info.name,
            'password': resp['token']
          };

          $scope.showRegenerateToken = false;
          $scope.tokenRegenerated = false;
        }, ApiService.errorDisplay('Could not load robot information', function() {
          $scope.credentials = null;
        }));
      };

      $scope.askRegenerateToken = function() {
        if ($scope.inReadOnlyMode) {
          return;
        }

        $scope.showRegenerateToken = true;
      };

      $scope.regenerateToken = function() {
        if ($scope.inReadOnlyMode) {
          return;
        }

        var pieces = $scope.info.name.split('+');
        var shortName = pieces[1];

        var organization = UserService.isOrganization(pieces[0]) ? pieces[0] : null;
        ApiService.regenerateRobotToken(organization, null, {'robot_shortname': shortName}).then(function(updated) {
          $scope.credentials = {
            'username': $scope.info.name,
            'password': updated['token']
          };
          $scope.showRegenerateToken = false;
          $scope.tokenRegenerated = true;
        }, ApiService.errorDisplay('Cannot regenerate robot account token'))
      };

      $scope.$watch('info', function(info) {
        if (info && info.name) {
          lookupRobot();
        }
      });
    }
  };
  return directiveDefinitionObject;
});