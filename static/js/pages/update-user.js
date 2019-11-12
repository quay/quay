(function() {
  /**
   * Update user page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('update-user', 'update-user.html', UpdateUserCtrl, {
      'title': 'Confirm Username'
    });
  }]);

  function UpdateUserCtrl($scope, UserService, $location, ApiService) {
    $scope.state = 'loading';
    $scope.metadata = {};

    UserService.updateUserIn($scope, function(user) {
      if (!user.anonymous) {
        if (!user.prompts || !user.prompts.length) {
            $location.path('/');
            return;
        }

        $scope.state = 'editing';
        $scope.username = user.username;
      }
    });

    var confirmUsername = function(username) {
        if (username == $scope.user.username) {
            $scope.state = 'confirmed';
            return;
        }

        $scope.state = 'confirming';
        var params = {
            'username': username
        };

        var oparams = {
          'orgname': username
        };

        ApiService.getUserInformation(null, params).then(function() {
          $scope.state = 'existing';
        }, function(resp) {
          ApiService.getOrganization(null, oparams).then(function() {
            $scope.state = 'existing';            
          }, function() {
            if (resp.status == 404) {
              $scope.state = 'confirmed';
            } else {
              $scope.state = 'error';
            }
          });
        });
    };

    $scope.updateUser = function(data) {
      $scope.state = 'updating';
      var errorHandler = ApiService.errorDisplay('Could not update user information', function() {
        $scope.state = 'editing';
      });

      ApiService.changeUserDetails(data).then(function() {
        UserService.load(function(updated) {
          if (updated && updated.prompts && updated.prompts.length) {
            $scope.state = 'editing';
          } else {
            $location.url('/');
          }
        });
      }, errorHandler);
    };

    $scope.hasPrompt = function(user, prompt_name) {
      if (!user || !user.prompts) {
        return false;
      }

      for (var i = 0; i < user.prompts.length; ++i) {
        if (user.prompts[i] == prompt_name) {
          return true;
        }
      }

      return false;
    };

    $scope.$watch('username', function(username) {
        if (!username) {
            $scope.state = 'editing';
            return;
        }

        confirmUsername(username);
    });
  }
})();
