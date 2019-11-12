(function() {
  /**
   * Page to view the members of a team and add/remove them.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('team-view', 'team-view.html', TeamViewCtrl, {
      'newLayout': true,
      'title': 'Team {{ teamname }}',
      'description': 'Team {{ teamname }}'
    })
  }]);

  function TeamViewCtrl($rootScope, $scope, $timeout, Features, Restangular, ApiService,
                        $routeParams, StateService) {
    var teamname = $routeParams.teamname;
    var orgname = $routeParams.orgname;

    $scope.inReadOnlyMode = StateService.inReadOnlyMode();
    $scope.context = {};
    $scope.orgname = orgname;
    $scope.teamname = teamname;
    $scope.addingMember = false;
    $scope.memberMap = null;
    $scope.allowEmail = Features.MAILING;
    $scope.feedback = null;
    $scope.allowedEntities = ['user', 'robot'];

    $rootScope.title = 'Loading...';

    $scope.filterFunction = function(invited, robots) {
      return function(item) {
        // Note: The !! is needed because is_robot will be undefined for invites.
        var robot_check = (!!item.is_robot == robots);
        return robot_check && item.invited == invited;
      };
    };

    $scope.inviteEmail = function(email) {
      if (!email || $scope.memberMap[email]) { return; }

      $scope.addingMember = true;

      var params = {
        'orgname': orgname,
        'teamname': teamname,
        'email': email
      };

      var errorHandler = ApiService.errorDisplay('Cannot invite team member', function() {
        $scope.addingMember = false;
      });

      ApiService.inviteTeamMemberEmail(null, params).then(function(resp) {
        $scope.members.push(resp);
        $scope.memberMap[resp.email] = resp;
        $scope.addingMember = false;

         $scope.feedback = {
            'kind': 'success',
            'message': 'E-mail address {email} was invited to join the team',
            'data': {
              'email': email
            }
          };
      }, errorHandler);
    };

    $scope.addNewMember = function(member) {
      if (!member || $scope.memberMap[member.name]) { return; }

      var params = {
        'orgname': orgname,
        'teamname': teamname,
        'membername': member.name
      };

      var errorHandler = ApiService.errorDisplay('Cannot add team member', function() {
        $scope.addingMember = false;
      });

      $scope.addingMember = true;
      ApiService.updateOrganizationTeamMember(null, params).then(function(resp) {
        $scope.members.push(resp);
        $scope.memberMap[resp.name] = resp;
        $scope.addingMember = false;

        $scope.feedback = {
          'kind': 'success',
          'message': 'User {username} was added to the team',
          'data': {
            'username': member.name
          }
        };
      }, errorHandler);
    };

    $scope.revokeInvite = function(inviteInfo) {
      if (inviteInfo.kind == 'invite') {
        // E-mail invite.
        $scope.revokeEmailInvite(inviteInfo.email);
      } else {
        // User invite.
        $scope.removeMember(inviteInfo.name);
      }
    };

    $scope.revokeEmailInvite = function(email) {
      var params = {
        'orgname': orgname,
        'teamname': teamname,
        'email': email
      };

      ApiService.deleteTeamMemberEmailInvite(null, params).then(function(resp) {
        if (!$scope.memberMap[email]) { return; }
        var index = $.inArray($scope.memberMap[email], $scope.members);
        $scope.members.splice(index, 1);
        delete $scope.memberMap[email];

        $scope.feedback = {
          'kind': 'success',
          'message': 'Invitation to e-amil address {email} was revoked',
          'data': {
            'email': email
          }
        };
      }, ApiService.errorDisplay('Cannot revoke team invite'));
    };

    $scope.removeMember = function(username) {
      var params = {
        'orgname': orgname,
        'teamname': teamname,
        'membername': username
      };

      ApiService.deleteOrganizationTeamMember(null, params).then(function(resp) {
        if (!$scope.memberMap[username]) { return; }
        var index = $.inArray($scope.memberMap[username], $scope.members);
        $scope.members.splice(index, 1);
        delete $scope.memberMap[username];

        $scope.feedback = {
          'kind': 'success',
          'message': 'User {username} was removed from the team',
          'data': {
            'username': username
          }
        };
      }, ApiService.errorDisplay('Cannot remove team member'));
    };

    $scope.getServiceName = function(service) {
      switch (service) {
        case 'ldap':
          return 'LDAP';

        case 'keystone':
          return 'Keystone Auth';

        case 'jwtauthn':
          return 'External JWT Auth';

        default:
          return synced.service;
      }
    };

    $scope.getAddPlaceholder = function(email, synced) {
      var kinds = [];

      if (!synced) {
        kinds.push('registered user');
      }

      kinds.push('robot');

      if (email && !synced) {
        kinds.push('email address');
      }

      kind_string = kinds.join(', ')
      return 'Add a ' + kind_string + ' to the team';
    };

    $scope.updateForDescription = function(content) {
      $scope.organization.teams[teamname].description = content;

      var params = {
        'orgname': orgname,
        'teamname': teamname
      };

      var teaminfo = $scope.organization.teams[teamname];
      ApiService.updateOrganizationTeam(teaminfo, params).then(function(resp) {
        $scope.feedback = {
          'kind': 'success',
          'message': 'Team description changed',
          'data': {}
        };
      }, function() {
        $('#cannotChangeTeamModal').modal({});
      });
    };

    $scope.showEnableSyncing = function() {
      $scope.enableSyncingInfo = {
        'service_info': $scope.canSync,
        'config': {}
      };
    };

    $scope.showDisableSyncing = function() {
      msg = 'Are you sure you want to disable group syncing on this team? ' +
            'The team will once again become editable.';
      bootbox.confirm(msg, function(result) {
        if (result) {
          $scope.disableSyncing();
        }
      });
    };

    $scope.disableSyncing = function() {
      var params = {
        'orgname': orgname,
        'teamname': teamname
      };

      var errorHandler = ApiService.errorDisplay('Could not disable team syncing');
      ApiService.disableOrganizationTeamSync(null, params).then(function(resp) {
        loadMembers();
      }, errorHandler);
    };

    $scope.enableSyncing = function(config, callback) {
      var params = {
        'orgname': orgname,
        'teamname': teamname
      };

      var errorHandler = ApiService.errorDisplay('Cannot enable team syncing', callback);
      ApiService.enableOrganizationTeamSync(config, params).then(function(resp) {
        loadMembers();
        callback(true);
      }, errorHandler);
    };

    var loadOrganization = function() {
      $scope.orgResource = ApiService.getOrganizationAsResource({'orgname': orgname}).get(function(org) {
        $scope.organization = org;
        $scope.team = $scope.organization.teams[teamname];
        $rootScope.title = teamname + ' (' + $scope.orgname + ')';
        $rootScope.description = 'Team management page for team ' + teamname + ' under organization ' + $scope.orgname;
        loadMembers();
        return org;
      });
    };

    var loadMembers = function() {
      var params = {
        'orgname': orgname,
        'teamname': teamname,
        'includePending': true
      };

      $scope.membersResource = ApiService.getOrganizationTeamMembersAsResource(params).get(function(resp) {
        $scope.members = resp.members;
        $scope.canEditMembers = resp.can_edit;
        $scope.canSync = resp.can_sync;
        $scope.syncInfo = resp.synced;
        $scope.allowedEntities = resp.synced ? ['robot'] : ['user', 'robot'];

        $('.info-icon').popover({
          'trigger': 'hover',
          'html': true
        });

        $scope.memberMap = {};
        for (var i = 0; i < $scope.members.length; ++i) {
          var current = $scope.members[i];
          $scope.memberMap[current.name || current.email] = current;
        }

        return resp.members;
      });
    };

    // Load the organization.
    loadOrganization();
  }
})();