/**
 * Element for managing the teams of an organization.
 */
angular.module('quay').directive('teamsManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/teams-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'organization': '=organization',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService, $timeout, UserService, TableService,
                         UIService, Config, Features, $location, StateService) {
      $scope.TableService = TableService;
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.Config = Config;
      $scope.Features = Features;

      $scope.views = Object.freeze({
        TEAMS: 0,
        MEMBERS: 1,
        COLLABORATORS: 2
      });

      $scope.options = {
        'predicate': 'ordered_team_index',
        'reverse': false,
        'filter': ''
      };

      $scope.teamRoles = [
          { 'id': 'member', 'title': 'Member', 'kind': 'default' },
          { 'id': 'creator', 'title': 'Creator', 'kind': 'success' },
          { 'id': 'admin', 'title': 'Admin', 'kind': 'primary' }
      ];

      UserService.updateUserIn($scope);

      $scope.teams = null;
      $scope.orderedTeams = null;
      $scope.showingMembers = false;
      $scope.fullMemberList = null;
      $scope.collaboratorList = null;
      $scope.userView = null;
      $scope.feedback = null;
      $scope.createTeamInfo = null;
      $scope.activeView = $scope.views.TEAMS;

      var getRoleIndex = function(name) {
        for (var i = 0; i < $scope.teamRoles.length; ++i) {
          if ($scope.teamRoles[i]['id'] == name) {
            return i;
          }
        }

        return -1;
      };

      var setTeamsState = function() {
        if (!$scope.organization || !$scope.organization.ordered_teams || !$scope.isEnabled) {
          return;
        }

        $scope.teams = [];
        $scope.organization.ordered_teams.map(function(name, index) {
          var team = $scope.organization.teams[name];
          team['ordered_team_index'] = $scope.organization.ordered_teams.length - index;
          team['role_index'] = getRoleIndex(team['role']);
          $scope.teams.push(team);
        });

        $scope.orderedTeams = TableService.buildOrderedItems(
            $scope.teams, $scope.options,
            ['name'],
            ['ordered_team_index', 'member_count', 'repo_count', 'role_index']);
      };

      var loadMembers = function(callback) {
        var params = {
          'orgname': $scope.organization.name
        };

        ApiService.getOrganizationMembers(null, params).then(function(resp) {
          $scope.fullMemberList = resp['members'];
          callback();
        }, ApiService.errorDisplay('Could not load full membership list'));
      };

      var loadCollaborators = function(callback) {
        var params = {
          'orgname': $scope.organization.name
        };

        ApiService.getOrganizationCollaborators(null, params).then(function(resp) {
          $scope.collaboratorList = resp['collaborators'];
          callback();
        }, ApiService.errorDisplay('Could not load collaborators list'));
      };

      $scope.setActiveView = function(view) {
        switch(view) {
        case $scope.views.TEAMS:
          // Nothing to do here.
          break;

        case $scope.views.MEMBERS:
          if (!$scope.fullMemberList) {
            loadMembers(function() {
              $scope.usersView = $scope.fullMemberList;
            });
          }

          $scope.usersView = $scope.fullMemberList;
          break;

        case $scope.views.COLLABORATORS:
          if (!$scope.collaboratorList) {
            loadCollaborators(function() {
              $scope.usersView = $scope.collaboratorList;
            });
          }

          $scope.usersView = $scope.collaboratorList;
          break;

        default:
          console.error('Invalid team-manager view: ' + view);
          return;
        }

        $scope.activeView = view;
      }

      $scope.setRole = function(role, teamname) {
        var previousRole = $scope.organization.teams[teamname].role;
        $scope.organization.teams[teamname].role = role;

        var params = {
          'orgname': $scope.organization.name,
          'teamname': teamname
        };

        var data = $scope.organization.teams[teamname];

        var errorHandler = ApiService.errorDisplay('Cannot update team', function(resp) {
          $scope.organization.teams[teamname].role = previousRole;
        });

        ApiService.updateOrganizationTeam(data, params).then(function(resp) {
          $scope.feedback = {
            'kind': 'success',
            'message': 'Team {team} role changed to {role}',
            'data': {
              'team': teamname,
              'role': role
            }
          };
        }, errorHandler);
      };

      $scope.askCreateTeam = function(teamname) {
        $scope.createTeamInfo = {
          'namespace': $scope.organization.name
        };
      };

      $scope.handleTeamCreated = function(created) {
        if (!created.new_team) {
          return;
        }

        var teamname = created.name;
        created['member_count'] = 0;

        $scope.organization.teams[teamname] = created;
        $scope.organization.ordered_teams.push(teamname);
        $scope.orderedTeams.push(created);

        $scope.feedback = {
          'kind': 'success',
          'message': 'Team {team} created',
          'data': {
            'team': teamname
          }
        };
      };

      $scope.askDeleteTeam = function(teamname) {
        bootbox.confirm('Are you sure you want to delete team ' + teamname + '?', function(resp) {
          if (resp) {
            $scope.deleteTeam(teamname);
          }
        });
      };

      $scope.deleteTeam = function(teamname) {
        var params = {
          'orgname': $scope.organization.name,
          'teamname': teamname
        };

        ApiService.deleteOrganizationTeam(null, params).then(function() {
          var index = $scope.organization.ordered_teams.indexOf(teamname);
          if (index >= 0) {
            $scope.organization.ordered_teams.splice(index, 1);
          }

          delete $scope.organization.teams[teamname];
          setTeamsState();

          $scope.feedback = {
            'kind': 'success',
            'message': 'Team {team} deleted',
            'data': {
              'team': teamname
            }
          };
        }, ApiService.errorDisplay('Cannot delete team'));
      };

      $scope.viewTeam = function(teamName) {
        $location.path('/organization/' + $scope.organization.name + '/teams/' + teamName);
      };

      $scope.removeMember = function(memberInfo, callback) {
        var params = {
          'orgname': $scope.organization.name,
          'membername': memberInfo.name
        };

        var errorHandler = ApiService.errorDisplay('Could not remove member', function() {
          callback(false);
        });

        ApiService.removeOrganizationMember(null, params).then(function(resp) {
          // Reset the state of the directive.
          $scope.fullMemberList = null;
          $scope.collaboratorList = null;
          $scope.setActiveView($scope.activeView);

          callback(true);

          $scope.feedback = {
            'kind': 'success',
            'message': 'User {user} removed from the organization',
            'data': {
              'user': memberInfo.name
            }
          };
        }, errorHandler)
      };

      $scope.askRemoveMember = function(memberInfo) {
        $scope.removeMemberInfo = $.extend({}, memberInfo);
      };

      $scope.setRepoPermissions = function(teamName) {
        if ($scope.inReadOnlyMode) { return; }

        $scope.setRepoPermissionsInfo = {
          'namespace': $scope.organization.name,
          'entityName': teamName,
          'entityKind': 'team',
          'entityIcon': 'fa-group'
        };
      };

      $scope.handlePermissionsSet = function(info, repositories) {
        var team = $scope.organization.teams[info.entityName];
        team['repo_count'] = repositories.length;
      };

      $scope.$watch('organization', setTeamsState);
      $scope.$watch('isEnabled', setTeamsState);

      $scope.$watch('options.predicate', setTeamsState);
      $scope.$watch('options.reverse', setTeamsState);
      $scope.$watch('options.filter', setTeamsState);
    }
  };

  return directiveDefinitionObject;
});
