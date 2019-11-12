/**
 * An element which displays a panel for managing users.
 */
angular.module('quay').directive('manageUserTab', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/manage-users-tab.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
        'isEnabled': '=isEnabled'
    },
    controller: function ($scope, $timeout, $location, $element, ApiService, UserService,
                          TableService, Features, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.Features = Features;
      $scope.user = UserService.currentUser();
      $scope.users = null;
      $scope.orderedUsers = [];
      $scope.usersPerPage = 10;

      $scope.newUser = {};
      $scope.createdUser = null;
      $scope.takeOwnershipInfo = null;
      $scope.options = {
        'predicate': 'username',
        'reverse': false,
        'filter': null,
        'page': 0
      };

      $scope.showCreateUser = function () {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.createdUser = null;
        $('#createUserModal').modal('show');
      };

      var sortUsers = function() {
        if (!$scope.users) {return;}
        $scope.orderedUsers = TableService.buildOrderedItems($scope.users, $scope.options,
                                                             ['username', 'email'], []);
      };

      var loadUsersInternal = function () {
        ApiService.listAllUsers().then(function (resp) {
          $scope.users = resp['users'];
          sortUsers();
          $scope.showInterface = true;
        }, function (resp) {
          $scope.users = [];
          $scope.usersError = ApiService.getErrorMessage(resp);
        });
      };
      $scope.tablePredicateClass = function(name, predicate, reverse) {
        if (name != predicate) {
          return '';
        }

        return 'current ' + (reverse ? 'reversed' : '');
      };

      $scope.orderBy = function(predicate) {
        if (predicate == $scope.options.predicate) {
          $scope.options.reverse = !$scope.options.reverse;
          return;
        }
        $scope.options.reverse = false;
        $scope.options.predicate = predicate;
      };

      $scope.createUser = function () {

        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.creatingUser = true;
        $scope.createdUser = null;

        var errorHandler = ApiService.errorDisplay('Cannot create user', function () {
          $scope.creatingUser = false;
          $('#createUserModal').modal('hide');
        });

        ApiService.createInstallUser($scope.newUser, null).then(function (resp) {
          $scope.creatingUser = false;
          $scope.newUser = {};
          $scope.createdUser = resp;
          loadUsersInternal();
        }, errorHandler)
      };

      $scope.showChangeEmail = function (user) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.userToChange = user;
        $('#changeEmailModal').modal({});
      };

      $scope.changeUserEmail = function (user) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $('#changeEmailModal').modal('hide');

        var params = {
          'username': user.username
        };

        var data = {
          'email': user.newemail
        };

        ApiService.changeInstallUser(data, params).then(function (resp) {
          loadUsersInternal();
          user.email = user.newemail;
          delete user.newemail;
        }, ApiService.errorDisplay('Could not change user'));
      };

      $scope.showChangePassword = function (user) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.userToChange = user;
        $('#changePasswordModal').modal({});
      };

      $scope.changeUserPassword = function (user) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $('#changePasswordModal').modal('hide');

        var params = {
          'username': user.username
        };

        var data = {
          'password': user.password
        };

        ApiService.changeInstallUser(data, params).then(function (resp) {
          loadUsersInternal();
        }, ApiService.errorDisplay('Could not change user'));
      };

      $scope.sendRecoveryEmail = function (user) {
        var params = {
          'username': user.username
        };

        ApiService.sendInstallUserRecoveryEmail(null, params).then(function (resp) {
          bootbox.dialog({
            "message": "A recovery email has been sent to " + resp['email'],
            "title": "Recovery email sent",
            "buttons": {
              "close": {
                "label": "Close",
                "className": "btn-primary"
              }
            }
          });

        }, ApiService.errorDisplay('Cannot send recovery email'))
      };

      $scope.showDeleteUser = function (user) {
        if (user.username == UserService.currentUser().username) {
          bootbox.dialog({
            "message": 'Cannot delete yourself!',
            "title": "Cannot delete user",
            "buttons": {
              "close": {
                "label": "Close",
                "className": "btn-primary"
              }
            }
          });
          return;
        }

        $scope.userToDelete = user;
        $('#confirmDeleteUserModal').modal({});
      };

      $scope.deleteUser = function (user) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $('#confirmDeleteUserModal').modal('hide');

        var params = {
          'username': user.username
        };

        ApiService.deleteInstallUser(null, params).then(function (resp) {
          loadUsersInternal();
        }, ApiService.errorDisplay('Cannot delete user'));
      };

      $scope.askDisableUser = function (user) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        var message = 'Are you sure you want to disable this user? ' +
          'They will be unable to login, pull or push.';

        if (!user.enabled) {
          message = 'Are you sure you want to reenable this user? ' +
            'They will be able to login, pull or push.'
        }

        bootbox.confirm(message, function (resp) {
          if (resp) {
            var params = {
              'username': user.username
            };

            var data = {
              'enabled': !user.enabled
            };

            ApiService.changeInstallUser(data, params).then(function (resp) {
              loadUsersInternal();
            });
          }
        });
      };

      $scope.askTakeOwnership = function (entity) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.takeOwnershipInfo = {
          'entity': entity
        };
      };

      $scope.takeOwnership = function (info, callback) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        var errorDisplay = ApiService.errorDisplay('Could not take ownership of namespace', callback);
        var params = {
          'namespace': info.entity.username || info.entity.name
        };

        ApiService.takeOwnership(null, params).then(function () {
          callback(true);
          $location.path('/organization/' + params.namespace);
        }, errorDisplay)
      };

      $scope.$watch('isEnabled', function (value) {
        if (value) {
          if ($scope.users) {
            return;
          }
          loadUsersInternal();
        }
      });

      $scope.$watch('options.predicate', sortUsers);
      $scope.$watch('options.reverse', sortUsers);
      $scope.$watch('options.filter', sortUsers);
    }
  };
  return directiveDefinitionObject;
});
