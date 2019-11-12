/**
 * An element which displays a box for the user to recover their account.
 */
angular.module('quay').directive('recoveryForm', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/recovery-form.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
    },
    controller: function($scope, $location, $timeout, ApiService, KeyService, UserService, Config, Features) {
      $scope.Config = Config;
      $scope.Features = Features;

      $scope.sendRecovery = function() {
        $scope.sendingRecovery = true;

        ApiService.requestRecoveryEmail($scope.recovery).then(function(resp) {
          $scope.invalidRecovery = false;
          $scope.errorMessage = '';
          $scope.sent = resp;
          $scope.sendingRecovery = false;
        }, function(resp) {
          $scope.invalidRecovery = true;
          $scope.errorMessage = ApiService.getErrorMessage(resp, 'Cannot send recovery email');
          $scope.sent = null;
          $scope.sendingRecovery = false;
        });
      };
    }
  };
  return directiveDefinitionObject;
});
