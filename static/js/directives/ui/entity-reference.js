/**
 * An element which shows an icon and a name/title for an entity (user, org, robot, team),
 * optionally linking to that entity if applicable.
 */
angular.module('quay').directive('entityReference', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/entity-reference.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'entity': '=entity',
      'namespace': '=namespace',
      'showAvatar': '@showAvatar',
      'avatarSize': '@avatarSize'
    },
    controller: function($scope, $element, UserService, UtilService, Config) {
      $scope.robotToShow = null;

      $scope.getIsAdmin = function(namespace) {
        return UserService.isNamespaceAdmin(namespace);
      };

      $scope.getTitle = function(entity) {
        if (!entity) { return ''; }

        switch (entity.kind) {
          case 'org':
            return 'Organization';

          case 'team':
            return 'Team';

          case 'user':
            return entity.is_robot ? 'Robot Account' : 'User';
        }
      };

      $scope.getPrefix = function(name) {
        if (!name) { return ''; }
        var plus = name.indexOf('+');
        return name.substr(0, plus);
      };

      $scope.getShortenedName = function(name) {
        if (!name) { return ''; }
        var plus = name.indexOf('+');
        return name.substr(plus + 1);
      };

      $scope.showRobotCredentials = function() {
        $scope.robotToShow = {
          'name': $scope.entity.name
        };
      };
    }
  };
  return directiveDefinitionObject;
});
