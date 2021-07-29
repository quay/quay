/**
 * An element which displays the sign in form.
 */
angular.module('quay').directive('signinForm', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/signin-form.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'inviteCode': '=inviteCode',
      'redirectUrl': '=redirectUrl',
      'signInStarted': '&signInStarted',
      'signedIn': '&signedIn'
    },
    controller: function($scope, $location, $timeout, $interval, ApiService, KeyService, UserService, CookieService, Features, Config, ExternalLoginService, StateService) {
      $scope.tryAgainSoon = 0;
      $scope.tryAgainInterval = null;
      $scope.signingIn = false;
      $scope.EXTERNAL_LOGINS = ExternalLoginService.EXTERNAL_LOGINS;
      $scope.Features = Features;
      $scope.signInUser = {};
      $scope.inAccountRecoveryMode = StateService.inAccountRecoveryMode();

      $scope.markStarted = function() {
        $scope.signingIn = true;
        if ($scope.signInStarted != null) {
          $scope.signInStarted();
        }
      };

      $scope.cancelInterval = function() {
        $scope.tryAgainSoon = 0;

        if ($scope.tryAgainInterval) {
          $interval.cancel($scope.tryAgainInterval);
        }

        $scope.tryAgainInterval = null;
      };

      $scope.$watch('user.username', function() {
        $scope.cancelInterval();
      });

      $scope.$on('$destroy', function() {
        $scope.cancelInterval();
      });

      $scope.signin = function() {
        if ($scope.tryAgainSoon > 0 || !Features.DIRECT_LOGIN) { return; }

        var checkIfEmpty = function(fieldName) {
          if (!$scope.signInUser[fieldName]) {
            $scope.signInUser[fieldName] = $('#signin-' + fieldName).val() || '';
          }
        };

        // Check for empty username and/or password. If found, we try to manually retrieve
        // the values as some password managers will not call the necessary Angular events.
        checkIfEmpty('username');
        checkIfEmpty('password');

        // If still empty, don't submit.
        if (!$scope.signInUser.username) {
          $('#signin-username').focus();
          return;
        }

        if (!$scope.signInUser.password) {
          $('#signin-password').focus();
          return;
        }

        $scope.markStarted();
        $scope.cancelInterval();

        if ($scope.inviteCode) {
          $scope.signInUser['invite_code'] = $scope.inviteCode;
        }

        ApiService.signinUser($scope.signInUser).then(function() {
          $scope.signingIn = false;
          $scope.needsEmailVerification = false;
          $scope.invalidCredentials = false;
          $scope.invalidCredentialsMessage = null;

          if ($scope.signedIn != null) {
            $scope.signedIn();
          }

          // Load the newly created user.
          UserService.load();

          // Redirect to the specified page or the landing page
          // Note: The timeout of 500ms is needed to ensure dialogs containing sign in
          // forms get removed before the location changes.
          $timeout(function() {
            var redirectUrl = $scope.redirectUrl;
            if (redirectUrl == $location.path() || redirectUrl == null) {
              return;
            }

            if (redirectUrl) {
              window.location = redirectUrl
            } else {
              $location.path('/');
            }
          }, 500);
        }, function(result) {
          $scope.signingIn = false;

          if (!result || !result.status /* malformed response */) {
            return bootbox.alert(ApiService.getErrorMessage(result));
          }

          if (result.status == 429 /* try again later */) {
            $scope.needsEmailVerification = false;
            $scope.invalidCredentials = false;
            $scope.invalidCredentialsMessage = null;

            $scope.cancelInterval();

            $scope.tryAgainSoon = result.headers('Retry-After');
            $scope.tryAgainInterval = $interval(function() {
              $scope.tryAgainSoon--;
              if ($scope.tryAgainSoon <= 0) {
                $scope.cancelInterval();
              }
            }, 1000, $scope.tryAgainSoon);

            return;
          }

          if (!result.data || result.status == 400 /* bad request */) {
            return bootbox.alert(ApiService.getErrorMessage(result));
          }

          /* success - set scope values to response */
          $scope.needsEmailVerification = result.data.needsEmailVerification;
          $scope.invalidCredentials = result.data.invalidCredentials;
          $scope.invalidCredentialsMessage = result.data.message;
        });
      };
    }
  };
  return directiveDefinitionObject;
});
