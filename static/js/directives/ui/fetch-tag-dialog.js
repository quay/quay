/**
 * An element which adds a of dialog for fetching a tag.
 */
angular.module('quay').directive('fetchTagDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/fetch-tag-dialog.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'actionHandler': '=actionHandler'
    },
    controller: function($scope, $element, $timeout, ApiService, UserService, Config, Features) {
      $scope.clearCounter = 0;
      $scope.currentFormat = null;
      $scope.currentEntity = null;
      $scope.currentRobot = null;
      $scope.formats = [];
      $scope.currentRobotHasPermission = null;

      UserService.updateUserIn($scope, updateFormats);

      var updateFormats = function() {
        $scope.formats = [];

        $scope.formats.push({
          'title': 'Docker Pull (by tag)',
          'icon': 'docker-icon',
          'command': 'docker pull {hostname}/{namespace}/{name}:{tag}'
        });

        if ($scope.currentTag && $scope.currentTag.manifest_digest) {          
          $scope.formats.push({
            'title': 'Docker Pull (by digest)',
            'icon': 'docker-icon',
            'command': 'docker pull {hostname}/{namespace}/{name}@{manifest_digest}'
          });
        }
      };

      $scope.$watch('currentEntity', function(entity) {
        if (!entity) {
          $scope.currentRobot = null;
          return;
        }

        if ($scope.currentRobot && $scope.currentRobot.name == entity.name) {
          return;
        }

        $scope.currentRobot = null;
        $scope.currentRobotHasPermission = null;

        var parts = entity.name.split('+');
        var namespace = parts[0];
        var shortname = parts[1];

        var params = {
          'robot_shortname': shortname
        };

        var orgname = UserService.isOrganization(namespace) ? namespace : '';
        ApiService.getRobot(orgname, null, params).then(function(resp) {
          $scope.currentRobot = resp;
        }, ApiService.errorDisplay('Cannot download robot token'));

        var permParams = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'username': entity.name
        };

        ApiService.getUserTransitivePermission(null, permParams).then(function(resp) {
          $scope.currentRobotHasPermission = resp['permissions'].length > 0;
        });
      });

      $scope.getCommand = function(format, robot) {
        if (!format || !format.command) { return ''; }
        if (format.require_creds && !robot) { return ''; }

        var params = {
          'pull_user': robot ? robot.name : '',
          'pull_password': robot ? robot.token : '',
          'hostname': Config.getDomain(),
          'http': Config.getHttp(),
          'namespace': $scope.repository.namespace,
          'name': $scope.repository.name,
          'tag': $scope.currentTag.name,
          'manifest_digest': $scope.currentTag.manifest_digest
        };

        var value = format.command;
        for (var param in params) {
          if (!params.hasOwnProperty(param)) { continue; }
          value = value.replace('{' + param + '}', params[param]);
        }

        return value;
      };

      $scope.setFormat = function(format) {
        $scope.currentFormat = format;
      };

      $scope.actionHandler = {
        'askFetchTag': function(tag) {
          $scope.currentTag = tag;
          $scope.currentFormat = null;
          $scope.currentEntity = null;
          $scope.currentRobot = null;
          $scope.currentRobotHasPermission = null;

          $scope.clearCounter++;

          updateFormats();

          $element.find('#fetchTagDialog').modal({});
        }
      };
    }
  };
  return directiveDefinitionObject;
});
