/**
 * An element which displays a table of permissions on a repository and allows them to be
 * edited.
 */
angular.module('quay').filter('objectFilter', function() {
  return function(obj, filterFn) {
    if (!obj) { return []; }

    var result = [];
    angular.forEach(obj, function(value) {
      if (filterFn(value)) {
        result.push(value);
      }
    });

    return result;
  };
});

angular.module('quay').directive('repositoryPermissionsTable', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repository-permissions-table.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService, RolesService, $rootScope, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.permissionResources = {'team': {}, 'user': {}};
      $scope.permissionCache = {};
      $scope.permissions = {};

      var readRole = RolesService.repoRoles[0].id;

      $scope.addPermissionInfo = {
        'role': readRole
      };

      var loadAllPermissions = function() {
        if (!$scope.repository || !$scope.isEnabled) { return; }

        fetchPermissions('user');
        fetchPermissions('team');
      };

      var fetchPermissions = function(kind) {
        if ($scope.permissionResources[kind]['loading'] != null) {
          return;
        }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        var Kind = kind[0].toUpperCase() + kind.substring(1);
        var r = ApiService['listRepo' + Kind + 'PermissionsAsResource'](params).get(function(resp) {
          $scope.permissions[kind] = resp.permissions;
          return resp.permissions;
        });

        $scope.permissionResources[kind] = r;
      };

      $scope.$watch('repository', loadAllPermissions);
      $scope.$watch('isEnabled', loadAllPermissions);

      loadAllPermissions();

      $scope.buildEntityForPermission = function(permission, kind) {
        var key = permission.name + ':' + kind;
        if ($scope.permissionCache[key]) {
          return $scope.permissionCache[key];
        }

        return $scope.permissionCache[key] = {
          'kind': kind,
          'name': permission.name,
          'is_robot': permission.is_robot,
          'is_org_member': permission.is_org_member,
          'avatar': permission.avatar
        };
      };

      $scope.hasPermissions = function(teams, users) {
        if (teams && teams.value) {
          if (Object.keys(teams.value).length > 0) {
            return true;
          }
        }

        if (users && users.value) {
          if (Object.keys(users.value).length > 0) {
            return true;
          }
        }

        return false;
      };

      $scope.allEntries = function() {
        return true;
      };

      $scope.onlyRobot = function(permission) {
        return permission.is_robot == true;
      };

      $scope.onlyUser = function(permission) {
        return !permission.is_robot;
      };

      $scope.addPermission = function() {
        $scope.addPermissionInfo['working'] = true;
        $scope.addNewPermission($scope.addPermissionInfo.entity, $scope.addPermissionInfo.role)
      };

      $scope.grantPermission = function(entity, callback) {
        $scope.addRole(entity.name, 'read', entity.kind, callback);
      };

      $scope.addNewPermission = function(entity, opt_role) {
        // Don't allow duplicates.
        if (!entity || !entity.kind || $scope.permissions[entity.kind][entity.name]) {
          $scope.addPermissionInfo = {};
          return;
        }

        if (entity.is_org_member === false) {
          $scope.grantPermissionInfo = {
            'entity': entity
          };
          return;
        }

        $scope.addRole(entity.name, opt_role || 'read', entity.kind);
      };

      $scope.deleteRole = function(entityName, kind) {
        RolesService.deleteRepositoryRole($scope.repository, kind, entityName, function(status) {
          if (status) {
            delete $scope.permissions[kind][entityName];
          }
        });
      };

      $scope.addRole = function(entityName, role, kind, opt_callback) {
        RolesService.setRepositoryRole($scope.repository, role, kind, entityName, function(status, result) {
          $scope.addPermissionInfo = {
            'role': readRole
          };

          if (status) {
            $scope.permissions[kind][entityName] = result;
          }

          opt_callback && opt_callback(status);
        });
      };

      $scope.setRole = function(role, entityName, kind) {
        var currentRole = $scope.permissions[kind][entityName].role;
        RolesService.setRepositoryRole($scope.repository, role, kind, entityName, function(status) {
          if (status) {
            $scope.permissions[kind][entityName]['role'] = role;
          } else {
            $scope.permissions[kind][entityName]['role'] = currentRole;
          }
        });
      };
    }
  };
  return directiveDefinitionObject;
});