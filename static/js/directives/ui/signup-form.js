/**
 * An element which displays the sign up form.
 */
angular.module('quay').directive('signupForm', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/signup-form.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'inviteCode': '=inviteCode',
      'hideRegisteredMessage': '@hideRegisteredMessage',
      'userRegistered': '&userRegistered'
    },
    controller: function($scope, $location, $timeout, ApiService, KeyService, UserService, Config, ExternalLoginService) {
      $scope.awaitingConfirmation = false;
      $scope.registering = false;
      $scope.Config = Config;
      $scope.registerIssue = null;

      $scope.register = function() {
        $scope.registering = true;
        $scope.registerIssue = null;

        if ($scope.inviteCode) {
          $scope.newUser['invite_code'] = $scope.inviteCode;
        }

        ApiService.createNewUser($scope.newUser).then(function(resp) {
          $scope.registering  = false;
          $scope.awaitingConfirmation = !!resp['awaiting_verification'];

          if (Config.MIXPANEL_KEY) {
            mixpanel.alias($scope.newUser.username);
          }

          $scope.userRegistered({'username': $scope.newUser.username});

          if (!$scope.awaitingConfirmation && !$scope.inviteCode) {
            $location.path("/");

          }

          UserService.load();
        }, function(result) {
          $scope.registering  = false;
          $scope.registerIssue = ApiService.getErrorMessage(result);
        });
      };
    }
  };
  return directiveDefinitionObject;
});
