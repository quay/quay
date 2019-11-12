
/**
 * The application header bar.
 */
angular.module('quay').directive('headerBar', function () {
  var number = 0;
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/header-bar.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
    },
    controller: function($rootScope, $scope, $element, $location, $timeout, hotkeys, UserService,
          PlanService, ApiService, NotificationService, Config, Features,
          ExternalLoginService, StateService) {

      ExternalLoginService.getSingleSigninUrl(function(url) {
        $scope.externalSigninUrl = url;
      });

      var hotkeysAdded = false;
      var userUpdated = function(cUser) {
        $scope.searchingAllowed = Features.ANONYMOUS_ACCESS || !cUser.anonymous;

        if (hotkeysAdded) { return; }
        hotkeysAdded = true;

        // Register hotkeys.
        if (!cUser.anonymous) {
          hotkeys.add({
            combo: 'alt+c',
            description: 'Create new repository',
            callback: function(e) {
              e.preventDefault();
              e.stopPropagation();
              $location.url('/new');
            }
          });
        }
      };

      $scope.Config = Config;
      $scope.Features = Features;
      $scope.notificationService = NotificationService;
      $scope.searchingAllowed = false;
      $scope.showBuildDialogCounter = 0;

      // Monitor any user changes and place the current user into the scope.
      UserService.updateUserIn($scope, userUpdated);
      StateService.updateStateIn($scope, function(state) {
        $scope.inReadOnlyMode = state.inReadOnlyMode;
      });

      $scope.currentPageContext = {};

      $rootScope.$watch('currentPage.scope.viewuser', function(u) {
        $scope.currentPageContext['viewuser'] = u;
      });

      $rootScope.$watch('currentPage.scope.organization', function(o) {
        $scope.currentPageContext['organization'] = o;
      });

      $rootScope.$watch('currentPage.scope.repository', function(r) {
        $scope.currentPageContext['repository'] = r;
      });

      $scope.signout = function() {
        ApiService.logout().then(function() {
          UserService.load();
          $location.path('/');
        });
      };

      $scope.getEnterpriseLogo = function() {
        return Config.getEnterpriseLogo();
      };

      $scope.getNamespace = function(context) {
        if (!context) { return null; }

        if (context.repository && context.repository.namespace) {
          return context.repository.namespace;
        }

        if (context.organization && context.organization.name) {
          return context.organization.name;
        }

        if (context.viewuser && context.viewuser.username) {
          return context.viewuser.username;
        }

        return null;
      };

      $scope.canAdmin = function(namespace) {
        if (!namespace) { return false; }
        return UserService.isNamespaceAdmin(namespace);
      };

      $scope.isOrganization = function(namespace) {
        if (!namespace) { return false; }
        return UserService.isOrganization(namespace);
      };

      $scope.startBuild = function(context) {
        $scope.showBuildDialogCounter++;
      };

      $scope.handleBuildStarted = function(build, context) {
        $location.url('/repository/' + context.repository.namespace + '/' + context.repository.name + '/build/' + build.id);
      };

      $scope.handleRobotCreated = function(created, context) {
        var namespace = $scope.getNamespace(context);
        if (UserService.isOrganization(namespace)) {
          $location.url('/organization/' + namespace + '?tab=robots&showRobot=' + created.name);
        } else {
          $location.url('/user/' + namespace + '?tab=robots&showRobot=' + created.name);
        }
      };

      $scope.handleTeamCreated = function(created, context) {
        var namespace = $scope.getNamespace(context);
        $location.url('/organization/' + namespace + '/teams/' + created.name);
      };

      $scope.askCreateRobot = function(context) {
        var namespace = $scope.getNamespace(context);
        if (!namespace || !UserService.isNamespaceAdmin(namespace)) { return; }

        $scope.createRobotInfo = {
          'namespace': namespace
        };
      };

      $scope.askCreateTeam = function(context) {
        var namespace = $scope.getNamespace(context);
        if (!namespace || !UserService.isNamespaceAdmin(namespace)) { return; }

        $scope.createTeamInfo = {
          'namespace': namespace
        };
      };
    }
  };
  return directiveDefinitionObject;
});