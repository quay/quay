/**
 * An element which displays a box for the user to sign in, sign up and recover their account.
 */
angular.module('quay').directive('userSetup', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/user-setup.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'redirectUrl': '=redirectUrl',
      'inviteCode': '=inviteCode',

      'hideLogo': '@hideLogo',

      'signInStarted': '&signInStarted',
      'signedIn': '&signedIn',
      'userRegistered': '&userRegistered'
    },
    controller: function($scope, $location, $timeout, ApiService, KeyService, UserService, Config, Features, StateService) {
      $scope.Config = Config;
      $scope.Features = Features;
      $scope.currentView = 'signin';
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.inAccountRecoveryMode = StateService.inAccountRecoveryMode();

      $scope.setView = function(view) {
        $scope.currentView = view;
      };

      $scope.handleUserRegistered = function(username) {
        $scope.userRegistered({'username': username});
      };
    }
  };
  return directiveDefinitionObject;
});
