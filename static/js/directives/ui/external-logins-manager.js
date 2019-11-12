/**
 * Element for managing the applications authorized by a user.
 */
angular.module('quay').directive('externalLoginsManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/external-logins-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'user': '=user',
    },
    controller: function($scope, $element, ApiService, UserService, Features, Config, KeyService,
                         ExternalLoginService) {
      $scope.Features = Features;
      $scope.Config = Config;
      $scope.KeyService = KeyService;

      $scope.EXTERNAL_LOGINS = ExternalLoginService.EXTERNAL_LOGINS;
      $scope.externalLoginInfo = {};
      $scope.hasSingleSignin = ExternalLoginService.hasSingleSignin();

      UserService.updateUserIn($scope, function(user) {
        $scope.cuser = jQuery.extend({}, user);
        $scope.externalLoginInfo = {};

        if ($scope.cuser.logins) {
          for (var i = 0; i < $scope.cuser.logins.length; i++) {
            var login = $scope.cuser.logins[i];
            login.metadata = login.metadata || {};
            $scope.externalLoginInfo[login.service] = login;
          }
        }
      });

      $scope.detachExternalLogin = function(service_id) {
        if (!Features.DIRECT_LOGIN) { return; }

        var params = {
          'service_id': service_id
        };

        ApiService.detachExternalLogin(null, params).then(function() {
          UserService.load();
        }, ApiService.errorDisplay('Count not detach service'));
      };
    }
  };
  return directiveDefinitionObject;
});