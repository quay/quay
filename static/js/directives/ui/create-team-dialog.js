/**
 * An element which displays a dialog for creating a team.
 */
angular.module('quay').directive('createTeamDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/create-team-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'info': '=info',
      'teamCreated': '&teamCreated'
    },
    controller: function($scope, $element, ApiService, UserService, NAME_PATTERNS) {
      $scope.TEAM_PATTERN = NAME_PATTERNS.TEAM_PATTERN;

      $scope.teamFinished = function(team) {
        $scope.teamCreated({'team': team});
      };

      $scope.createTeam = function(name, callback) {
        var data = {
          'name': name,
          'role': 'member'
        };

        var params = {
          'orgname': $scope.info.namespace,
          'teamname': name
        };

        var errorDisplay = ApiService.errorDisplay('Cannot create team', function() {
          callback(null);
        });

        ApiService.updateOrganizationTeam(data, params).then(function(resp) {
          if (!resp.new_team) {
            callback(null);
            bootbox.alert('Team with name "' + resp.name + '" already exists')
            return;
          }
          callback(resp);
        }, errorDisplay);
      };
    }
  };
  return directiveDefinitionObject;
});