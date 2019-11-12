/**
 * Element for managing the robots owned by an organization or a user.
 */
angular.module('quay').directive('robotsManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/robots-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'organization': '=organization',
      'user': '=user',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService, $routeParams, Config, $rootScope,
                         TableService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.robots = null;
      $scope.loading = false;
      $scope.Config = Config;
      $scope.TableService = TableService;
      $scope.feedback = null;

      $scope.robotDisplayInfo = null;
      $scope.createRobotInfo = null;

      $scope.options = {
        'filter': null,
        'predicate': 'name',
        'reverse': false,
      };

      var buildOrderedRobots = function() {
        if (!$scope.robots) {
          return;
        }

        var robots = $scope.robots;
        robots.forEach(function(robot) {
          robot['teams_string'] = robot.teams.map(function(team) {
            return team['name'] || '';
          }).join(',');

          robot['created_datetime'] = robot.created ? TableService.getReversedTimestamp(robot.created) : null;
          robot['last_accessed_datetime'] = robot.last_accessed ? TableService.getReversedTimestamp(robot.last_accessed) : null;
        });

        $scope.orderedRobots = TableService.buildOrderedItems(robots, $scope.options,
                                                              ['name', 'teams_string'], []);
      };

      $scope.showRobot = function(info) {
        $scope.robotDisplayInfo = {
          'name': info.name
        };
      };

      $scope.findRobotIndexByName = function(name) {
        if (!$scope.robots) { return -1; }

        for (var i = 0; i < $scope.robots.length; ++i) {
          if ($scope.robots[i].name == name) {
            return i;
          }
        }
        return -1;
      };

      $scope.getShortenedRobotName = function(info) {
        return $scope.getShortenedName(info.name);
      };

      $scope.getShortenedName = function(name) {
        var plus = name.indexOf('+');
        return name.substr(plus + 1);
      };

      $scope.getPrefix = function(name) {
        var plus = name.indexOf('+');
        return name.substr(0, plus);
      };

      $scope.askCreateRobot = function() {
        $scope.createRobotInfo = {
          'namespace': $scope.organization ? $scope.organization.name : $scope.user.username
        };
      };

      $scope.deleteRobot = function(info) {
        var shortName = $scope.getShortenedName(info.name);
        ApiService.deleteRobot($scope.organization, null, {'robot_shortname': shortName}).then(function(resp) {
          var index = $scope.findRobotIndexByName(info.name);
          if (index >= 0) {
            $scope.robots.splice(index, 1);
            $scope.feedback = {
              'kind': 'success',
              'message': 'Robot account {robot} was deleted',
              'data': {
                'robot': info.name
              }
            };
            buildOrderedRobots();
          }
        }, ApiService.errorDisplay('Cannot delete robot account'));
      };

      $scope.askDeleteRobot = function(info) {
        bootbox.confirm('Are you sure you want to delete robot ' + info.name + '?', function(resp) {
          if (resp) {
            $scope.deleteRobot(info);
          }
        });
      };

      $scope.setPermissions = function(info) {
        if (!($scope.user || ($scope.organization && $scope.organization.is_admin)) || $scope.inReadOnlyMode) { return; }
        
        var namespace = $scope.organization ? $scope.organization.name : $scope.user.username;
        $scope.setRepoPermissionsInfo = {
          'namespace': namespace,
          'entityName': info.name,
          'entityKind': 'robot',
          'entityIcon': 'ci-robot'
        };
      };

      $scope.handlePermissionsSet = function(info, repositories) {
        var index = $scope.findRobotIndexByName(info.entityName);
        $scope.robots[index]['repositories'] = repositories;
      };

      $scope.robotCreated = function() {
        update();
      };

      var update = function() {
        if (!$scope.user && !$scope.organization) { return; }
        if ($scope.loading || !$scope.isEnabled) { return; }

        var params = {
          'permissions': true,
          'token': false
        };

        $scope.loading = true;
        ApiService.getRobots($scope.organization, null, params).then(function(resp) {
          $scope.robots = resp.robots;
          buildOrderedRobots();
          $scope.loading = false;
        });
      };

      $scope.$watch('isEnabled', update);
      $scope.$watch('organization', update);
      $scope.$watch('user', update);
      $scope.$watch('options.filter', buildOrderedRobots);
      $scope.$watch('options.predicate', buildOrderedRobots);
      $scope.$watch('options.reverse', buildOrderedRobots);
    }
  };
  return directiveDefinitionObject;
});