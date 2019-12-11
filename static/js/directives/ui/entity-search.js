/**
 * An element which displays a box to search for an entity (org, user, robot, team). This control
 * allows for filtering of the entities found and whether to allow selection by e-mail.
 */
angular.module('quay').directive('entitySearch', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/entity-search.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    require: '?ngModel',
    link: function(scope, element, attr, ctrl) {
      scope.ngModel = ctrl;
    },
    scope: {
      'namespace': '=namespace',
      'placeholder': '=placeholder',
      'forRepository': '=forRepository',
      'skipPermissions': '=skipPermissions',

      // Default: ['user', 'team', 'robot']
      'allowedEntities': '=allowedEntities',

      'currentEntity': '=currentEntity',

      'entitySelected': '&entitySelected',
      'emailSelected': '&emailSelected',

      // When set to true, the contents of the control will be cleared as soon
      // as an entity is selected.
      'autoClear': '=autoClear',

      // Set this property to immediately clear the contents of the control.
      'clearValue': '=clearValue',

      // Whether e-mail addresses are allowed.
      'allowEmails': '=allowEmails',
      'emailMessage': '@emailMessage',

      // True if the menu should pull right.
      'pullRight': '@pullRight'
    },
    controller: function($rootScope, $scope, $element, Restangular, UserService, ApiService, UtilService, AvatarService, Config, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.requiresLazyLoading = true;
      $scope.isLazyLoading = false;
      $scope.userRequestedLazyLoading = false;

      $scope.teams = null;
      $scope.page = {};
      $scope.page.robots = null;

      $scope.isAdmin = false;
      $scope.isOrganization = false;

      $scope.includeTeams = true;
      $scope.includeRobots = true;
      $scope.includeOrgs = false;

      $scope.currentEntityInternal = $scope.currentEntity;
      $scope.createRobotInfo = null;
      $scope.createTeamInfo = null;

      $scope.Config = Config;

      var isSupported = function(kind, opt_array) {
        return $.inArray(kind, opt_array || $scope.allowedEntities || ['user', 'team', 'robot']) >= 0;
      };

      var resetCache = function() {
        $scope.requiresLazyLoading = true;

        $scope.teams = null;
        $scope.page.robots = null;
      };

      $scope.lazyLoad = function() {
        $scope.userRequestedLazyLoading = true;
        $scope.checkLazyLoad();
      };

      $scope.checkLazyLoad = function() {
        if (!$scope.namespace || !$scope.thisUser || !$scope.requiresLazyLoading ||
             $scope.isLazyLoading || !$scope.userRequestedLazyLoading) {
            return;
        }

        $scope.isLazyLoading = true;
        $scope.isAdmin = UserService.isNamespaceAdmin($scope.namespace);
        $scope.isOrganization = !!UserService.getOrganization($scope.namespace);

        // Reset the cached teams and robots, just to be sure.
        $scope.teams = null;
        $scope.page.robots = null;

        var requiredOperations = 0;
        var operationComplete = function() {
          requiredOperations--;
          if (requiredOperations <= 0) {
            $scope.isLazyLoading = false;
            $scope.requiresLazyLoading = false;
          }
        };

        // Load the organization's teams (if applicable).
        if ($scope.isOrganization && isSupported('team')) {
          requiredOperations++;

          // Note: We load the org here directly so that we always have the fully up-to-date
          // teams list.
          ApiService.getOrganization(null, {'orgname': $scope.namespace}).then(function(resp) {
            $scope.teams = Object.keys(resp.teams).map(function(key) {
              return resp.teams[key];
            });
            operationComplete();
          }, operationComplete);
        }

        // Load the user/organization's robots (if applicable).
        if ($scope.isAdmin && isSupported('robot')) {
          requiredOperations++;
          var params = {
            'token': false,
            'limit': 20
          };

          ApiService.getRobots($scope.isOrganization ? $scope.namespace : null, null, params).then(function(resp) {
            $scope.page.robots = resp.robots;
            operationComplete();
          }, operationComplete);
        }

        if (requiredOperations == 0) {
          operationComplete();
        }
      };

      $scope.askCreateTeam = function() {
        $scope.createTeamInfo = {
          'namespace': $scope.namespace,
          'repository': $scope.forRepository,
          'skip_permissions': $scope.skipPermissions
        };
      };

      $scope.askCreateRobot = function() {
        $scope.createRobotInfo = {
          'namespace': $scope.namespace,
          'repository': $scope.forRepository,
          'skip_permissions': $scope.skipPermissions
        };
      };

      $scope.handleTeamCreated = function(created) {
        $scope.setEntity(created.name, 'team', false, created.avatar);
        if (created.new_team) {
          $scope.teams.push(created);
        }
      };

      $scope.handleRobotCreated = function(created) {
        $scope.setEntity(created.name, 'user', true, created.avatar);
        $scope.page.robots.push(created);
      };

      $scope.setEntity = function(name, kind, is_robot, avatar) {
        var entity = {
          'name': name,
          'kind': kind,
          'is_robot': is_robot,
          'avatar': avatar
        };

        if ($scope.isOrganization) {
          entity['is_org_member'] = true;
        }

        $scope.setEntityInternal(entity, false);
      };

      $scope.clearEntityInternal = function() {
        $scope.currentEntityInternal = null;
        $scope.currentEntity = null;
        $scope.entitySelected({'entity': null});
        if ($scope.ngModel) {
          $scope.ngModel.$setValidity('entity', false);
        }
      };

      $scope.setEntityInternal = function(entity, updateTypeahead) {
        // If the entity is an external entity, convert it to a known user via an API call.
        if (entity.kind == 'external') {
          var params = {
            'username': entity.name
          };

          ApiService.linkExternalUser(null, params).then(function(resp) {
            $scope.setEntityInternal(resp['entity'], updateTypeahead);
          }, ApiService.errorDisplay('Could not link external user'));
          return;
        }

        if (updateTypeahead) {
          $(input).typeahead('val', $scope.autoClear ? '' : entity.name);
        } else {
          $(input).val($scope.autoClear ? '' : entity.name);
        }

        if (!$scope.autoClear) {
          $scope.currentEntityInternal = entity;
          $scope.currentEntity = entity;
        }

        $scope.entitySelected({'entity': entity});
        if ($scope.ngModel) {
          $scope.ngModel.$setValidity('entity', !!entity);
        }
      };

      // Setup the typeahead.
      var input = $element[0].firstChild.firstChild;

      (function() {
        // Create the bloodhound search query system.
        $rootScope.__entity_search_counter = (($rootScope.__entity_search_counter || 0) + 1);
        var entitySearchB = new Bloodhound({
          name: 'entities' + $rootScope.__entity_search_counter,
          remote: {
            url: '/api/v1/entities/%QUERY',
            replace: function (query_url, uriEncodedQuery) {
              $scope.lazyLoad();

              var namespace = $scope.namespace || '';

              var url = UtilService.getRestUrl(query_url.replace('%QUERY', uriEncodedQuery));
              url.setQueryParameter('namespace', namespace);

              if ($scope.isOrganization && isSupported('team')) {
                url.setQueryParameter('includeTeams', true);
              }

              if (isSupported('org')) {
                url.setQueryParameter('includeOrgs', true);
              }
              return url;
            },
            filter: function(data) {
              var datums = [];
              for (var i = 0; i < data.results.length; ++i) {
                var entity = data.results[i];

                var found = 'user';
                if (entity.kind == 'user' || entity.kind == 'external') {
                  found = entity.is_robot ? 'robot' : 'user';
                } else if (entity.kind == 'team') {
                  found = 'team';
                } else if (entity.kind == 'org') {
                  found = 'org';
                }

                if (!isSupported(found)) {
                  continue;
                }

                datums.push({
                  'value': entity.name,
                  'tokens': [entity.name],
                  'entity': entity
                });
              }
              return datums;
            }
          },
          datumTokenizer: function(d) {
            return Bloodhound.tokenizers.whitespace(d.val);
          },
          queryTokenizer: Bloodhound.tokenizers.whitespace
        });
        entitySearchB.initialize();

        // Setup the typeahead.
        $(input).typeahead({
          'highlight': true,
          'hint': false,
        }, {
          display: 'value',
          source: entitySearchB.ttAdapter(),
          templates: {
            'notFound': function(info) {
              // Only display the empty dialog if the server load has finished.
              if (info.resultKind == 'remote') {
                var val = $(input).val();
                if (!val) {
                  return null;
                }

                if (UtilService.isEmailAddress(val)) {
                  if ($scope.allowEmails) {
                    return '<div class="tt-message">' + $scope.emailMessage + '</div>';
                  } else {
                    return '<div class="tt-empty">A ' + Config.REGISTRY_TITLE_SHORT + ' username (not an e-mail address) must be specified</div>';
                  }
                }

                var classes = [];

                if (isSupported('user')) { classes.push('users'); }
                if (isSupported('org')) { classes.push('organizations'); }
                if ($scope.isAdmin && isSupported('robot')) { classes.push('robot accounts'); }
                if ($scope.isOrganization && isSupported('team')) { classes.push('teams'); }

                if (classes.length == 0) {
                  return '<div class="tt-empty">No matching entities found</div>';
                }

                var class_string = '';
                for (var i = 0; i < classes.length; ++i) {
                  if (i > 0) {
                    if (i == classes.length - 1) {
                      class_string += ' or ';
                    } else {
                      class_string += ', ';
                    }
                  }

                  class_string += classes[i];
                }

                return '<div class="tt-empty">No matching ' + Config.REGISTRY_TITLE_SHORT + ' ' + class_string + ' found</div>';
              }

              return null;
            },
            'suggestion': function (datum) {
              template = '<div class="entity-mini-listing">';
              if (Config['AVATAR_KIND'] === 'gravatar' &&
                 ((datum.entity.kind == 'user' && !datum.entity.is_robot) || (datum.entity.kind == 'org'))) {
                template += '<i class="fa"><img class="avatar-image" src="' +
                            AvatarService.getAvatar(datum.entity.avatar.hash, 20, 'mm') +
                            '"></i>';
              } else if (datum.entity.kind == 'external') {
                template += '<i class="fa fa-user fa-lg"></i>';
              } else if (datum.entity.kind == 'user' && datum.entity.is_robot) {
                template += '<i class="fa ci-robot fa-lg"></i>';
              } else if (datum.entity.kind == 'team') {
                template += '<i class="fa fa-group fa-lg"></i>';
              }

              template += '<span class="name">' + datum.value + '</span>';

              if (datum.entity.title) {
                template += '<span class="title">' + datum.entity.title + '</span>';
              }

              if (datum.entity.is_org_member === false && datum.entity.kind == 'user') {
                template += '<i class="fa fa-exclamation-triangle" title="User is outside the organization"></i>';
              }

              template += '</div>';
              return template;
            }}
        });

        $(input).on('keypress', function(e) {
          var val = $(input).val();
          var code = e.keyCode || e.which;
          if (code == 13 && $scope.allowEmails && UtilService.isEmailAddress(val)) {
            $scope.$apply(function() {
              $scope.emailSelected({'email': val});
            });
          }
        });

        $(input).on('input', function(e) {
          $scope.$apply(function() {
            $scope.clearEntityInternal();
          });
        });

        $(input).on('typeahead:selected', function(e, datum) {
          $scope.$apply(function() {
            $scope.setEntityInternal(datum.entity, true);
          });
        });
      })();

      $scope.$watch('clearValue', function() {
        if (!input) { return; }

        $(input).typeahead('val', '');
        $scope.clearEntityInternal();
      });

      $scope.$watch('placeholder', function(title) {
        input.setAttribute('placeholder', title);
      });

      $scope.$watch('allowedEntities', function(allowed) {
        if (!allowed) { return; }
        $scope.includeTeams = isSupported('team', allowed);
        $scope.includeRobots = isSupported('robot', allowed);
      });

      $scope.$watch('namespace', function(namespace) {
        if (!namespace) { return; }
        resetCache();
        $scope.checkLazyLoad();
      });

      UserService.updateUserIn($scope, function(currentUser){
        if (currentUser.anonymous) { return; }
        $scope.thisUser = currentUser;
        resetCache();
        $scope.checkLazyLoad();
      });

      $scope.$watch('currentEntity', function(entity) {
        if ($scope.currentEntityInternal != entity) {
          if (entity) {
            $scope.setEntityInternal(entity, false);
          } else {
            $scope.clearEntityInternal();
          }
        }
      });
    }
  };
  return directiveDefinitionObject;
});
