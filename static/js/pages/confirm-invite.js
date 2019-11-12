(function() {
  /**
   * Page for confirming an invite to a team.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('confirm-invite', 'confirm-invite.html', ConfirmInviteCtrl, {
      'title': 'Confirm Invitation'
    });
  }]);

  function ConfirmInviteCtrl($scope, $location, UserService, ApiService, NotificationService) {
    // Monitor any user changes and place the current user into the scope.
    $scope.loading = false;
    $scope.inviteCode = $location.search()['code'] || '';

    UserService.updateUserIn($scope, function(user) {
      if (!user.anonymous && !$scope.loading) {
        // Make sure to not redirect now that we have logged in. We'll conduct the redirect
        // manually.
        $scope.redirectUrl = null;
        $scope.loading = true;

        var params = {
          'code': $location.search()['code']
        };

        ApiService.acceptOrganizationTeamInvite(null, params).then(function(resp) {
          NotificationService.update();
          UserService.load();
          $location.path('/organization/' + resp.org + '/teams/' + resp.team);
        }, function(resp) {
          $scope.loading = false;
          $scope.invalid = ApiService.getErrorMessage(resp, 'Invalid confirmation code');
        });
      }
    });

    $scope.redirectUrl = window.location.href;
  }
})();