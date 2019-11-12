(function() {
  /**
   * Sign in page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('signin', 'signin.html', SignInCtrl, {
      'title': 'Sign In',
    });
  }]);

  function SignInCtrl($scope, $location, ExternalLoginService, Features) {
    $scope.redirectUrl = '/';

    ExternalLoginService.getSingleSigninUrl(function(singleUrl) {
      if (singleUrl) {
        document.location = singleUrl;
      }
    });
  }
})();
