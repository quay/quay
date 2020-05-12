(function() {
  /**
   * Page that displays details about an user.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('user-view', 'user-view.html', UserViewCtrl, {
      'newLayout': true,
      'title': 'User {{ user.username }}',
      'description': 'User {{ user.username }}'
    })
  }]);

  function UserViewCtrl($scope, $routeParams, $timeout, ApiService, UserService, UIService,
                        AvatarService, Config, ExternalLoginService, CookieService, StateService) {
    var username = $routeParams.username;

    $scope.inReadOnlyMode = StateService.inReadOnlyMode();
    $scope.Config = Config;

    $scope.showAppsCounter = 0;
    $scope.showRobotsCounter = 0;
    $scope.showBillingCounter = 0;
    $scope.showLogsCounter = 0;

    $scope.changeEmailInfo = null;
    $scope.changePasswordInfo = null;
    $scope.changeMetadataInfo = null;

    $scope.hasSingleSignin = ExternalLoginService.hasSingleSignin();
    $scope.context = {};

    $scope.oidcLoginProvider = null;

    if (Config['INTERNAL_OIDC_SERVICE_ID']) {
      ExternalLoginService.EXTERNAL_LOGINS.forEach(function(provider) {
        if (provider.id == Config['INTERNAL_OIDC_SERVICE_ID']) {
          $scope.oidcLoginProvider = provider;
        }
      });
    }

    UserService.updateUserIn($scope, function(user) {
      if (user && user.username) {
        if ($scope.oidcLoginProvider && $routeParams['idtoken']) {
          $scope.context.idTokenCredentials = {
            'username': UserService.getCLIUsername(),
            'password': $routeParams['idtoken'],
            'namespace': UserService.currentUser().username
          };
        }
      }
    });

    var loadRepositories = function() {
      var options = {
        'public': true,
        'namespace': username,
        'last_modified': true,
        'popularity': true
      };

      $scope.context.viewuser.repositories = ApiService.listReposAsResource().withPagination('repositories').withOptions(options).get(function(resp) {
        return resp.repositories;
      });
    };

    var loadUser = function() {
      $scope.userResource = ApiService.getUserInformationAsResource({'username': username}).get(function(user) {
        $scope.context.viewuser = user;
        $scope.viewuser = user;

        $timeout(function() {
          // Load the repositories.
          loadRepositories();

          // Show the password change dialog if immediately after an account recovery.
          if ($routeParams.action == 'password' && UserService.isNamespaceAdmin(username)) {
            $scope.showChangePassword();
          }
        }, 10);
      });
    };

    // Load the user.
    loadUser();

    $scope.showRobots = function() {
      $scope.showRobotsCounter++;
    };

    $scope.showLogs = function() {
      $scope.showLogsCounter++;
    };

    $scope.showApplications = function() {
      $scope.showAppsCounter++;
    };

    $scope.showChangePassword = function() {
      $scope.changePasswordInfo = {};
    };

    $scope.changePassword = function(info, callback) {
      if (Config.AUTHENTICATION_TYPE != 'Database') { return; }

      var data = {
        'password': $scope.changePasswordInfo.password
      };

      var errorDisplay = ApiService.errorDisplay('Could not change password', callback);

      ApiService.changeUserDetails(data).then(function(resp) {
        // Reload the user.
        UserService.load();
        callback(true);
      }, errorDisplay);
    };

    $scope.generateClientToken = function() {
      var generateToken = function(password) {
        if (!password) {
          return;
        }

        var data = {
          'password': password
        };

        ApiService.generateUserClientKey(data).then(function(resp) {
          $scope.context.encryptedPasswordCredentials = {
            'username': UserService.getCLIUsername(),
            'password': resp['key'],
            'namespace': UserService.currentUser().username
          };
        }, ApiService.errorDisplay('Could not generate token'));
      };

      UIService.showPasswordDialog('Enter your password to generate an encrypted version:', generateToken);
    };

    $scope.showChangeMetadata = function(field_name, field_title) {
      $scope.changeMetadataInfo = {
        'value': $scope.context.viewuser[field_name],
        'field': field_name,
        'title': field_title
      };
    };

    $scope.updateMetadataInfo = function(info, callback) {
      var details = {};
      details[info.field] = (info.value === '' ? null : info.value);

      var errorDisplay = ApiService.errorDisplay('Could not update ' + info.title, callback);
      
      ApiService.changeUserDetails(details).then(function() {
        $scope.context.viewuser[info.field] = info.value;
        callback(true);
      }, errorDisplay);
    };
      
    $scope.showChangeEmail = function() {
      $scope.changeEmailInfo = {
        'email': $scope.context.viewuser.email
      };
    };

    $scope.changeEmail = function(info, callback) {
      var details = {
        'email': $scope.changeEmailInfo.email
      };

      var errorDisplay = ApiService.errorDisplay('Could not change email address', callback);

      ApiService.changeUserDetails(details).then(function() {
        $scope.context.emailAwaitingChange = $scope.changeEmailInfo.email;
        callback(true);
      }, errorDisplay);
    };

    $scope.showChangeAccount = function() {
      $scope.convertAccountInfo = {
        'user': $scope.context.viewuser
      };
    };

    $scope.showBilling = function() {
      $scope.showBillingCounter++;
    };


    $scope.notificationsPermissionsEnabled = window['Notification']
      && Notification.permission === 'granted'
      && CookieService.get('quay.enabledDesktopNotifications') === 'on';

    $scope.desktopNotificationsPermissionIsDisabled = () => window['Notification'] && Notification.permission === 'denied';

    $scope.toggleDesktopNotifications = () => {
      if (!window['Notification']) { // unsupported in IE & some older browsers, we'll just tell the user it's not available
        bootbox.dialog({
          "message": 'Desktop Notifications unsupported in this browser',
          "title": 'Unsupported Option',
          "buttons": {
            "close": {
              "label": "Close",
              "className": "btn-primary"
            }
          }
        });

        return;
      }

      if (CookieService.get('quay.enabledDesktopNotifications') === 'on') {
        bootbox.confirm('Are you sure you want to turn off browser notifications?', confirmed => {
          if (confirmed) {
            CookieService.putPermanent('quay.enabledDesktopNotifications', 'off');
            CookieService.clear('quay.notifications.mostRecentTimestamp');

            $scope.$apply(() => {
              $scope.notificationsPermissionsEnabled = false;
            });
          }
        });
      } else {
        if (Notification.permission === 'default') {
          Notification.requestPermission()
            .then((newPermission) => {
              if (newPermission === 'granted') {
                CookieService.putPermanent('quay.enabledDesktopNotifications', 'on');
                CookieService.putPermanent('quay.notifications.mostRecentTimestamp', new Date().getTime().toString());
              }

              $scope.$apply(() => {
                  $scope.notificationsPermissionsEnabled = (newPermission === 'granted');
              });
            });
        } else if (Notification.permission === 'granted') {
          bootbox.confirm('Are you sure you want to turn on browser notifications?', confirmed => {
            if (confirmed) {
              CookieService.putPermanent('quay.enabledDesktopNotifications', 'on');
              CookieService.putPermanent('quay.notifications.mostRecentTimestamp', new Date().getTime().toString());

              $scope.$apply(() => {
                $scope.notificationsPermissionsEnabled = true;
              });
            }
          });
        }
      }
    };

  }
})();
