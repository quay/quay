/**
 * An element which displays a button for logging into the application via an external service.
 */
angular.module('quay').directive('externalLoginButton', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/external-login-button.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'signInStarted': '&signInStarted',
      'redirectUrl': '=redirectUrl',
      'isLink': '=isLink',
      'provider': '=provider',
      'action': '@action'
    },
    controller: function($scope, $timeout, $interval, ApiService, KeyService, CookieService, ExternalLoginService) {
      $scope.signingIn = false;

      $scope.startSignin = function() {
        $scope.signInStarted({'service': $scope.provider});
        ExternalLoginService.getLoginUrl($scope.provider, $scope.action || 'login', function(url) {
          // Save the redirect URL in a cookie so that we can redirect back after the service returns to us.
          var redirectURL = $scope.redirectUrl || window.location.toString();
          CookieService.putPermanent('quay.redirectAfterLoad', redirectURL);

          // Needed to ensure that UI work done by the started callback is finished before the location
          // changes.
          $scope.signingIn = true;
          $timeout(function() {
            document.location = url;
          }, 250);
        });
      };
    }
  };
  return directiveDefinitionObject;
});
