/**
 * Service which defines the various role groups.
 */
angular.module('quay').factory('RolesService', ['UtilService', 'Restangular', 'ApiService', 'UserService',
    function(UtilService, Restangular, ApiService, UserService) {
  var roleService = {};

  roleService.repoRolesOrNone = [
    { 'id': 'none', 'title': 'None', 'kind': 'default', 'description': 'No permissions on the repository' },

    { 'id': 'read', 'title': 'Read', 'kind': 'success', 'description': 'Can view and pull from the repository' },
    { 'id': 'write', 'title': 'Write', 'kind': 'success', 'description': 'Can view, pull and push to the repository' },
    { 'id': 'admin', 'title': 'Admin', 'kind': 'primary', 'description': 'Full admin access, pull and push on the repository' }
  ];

  roleService.repoRoles = roleService.repoRolesOrNone.slice(1);

  roleService.teamRoles = [
    { 'id': 'member', 'title': 'Member', 'kind': 'default', 'description': 'Inherits all permissions of the team' },
    { 'id': 'creator', 'title': 'Creator', 'kind': 'success', 'description': 'Member and can create new repositories' },
    { 'id': 'admin', 'title': 'Admin', 'kind': 'primary', 'description': 'Full admin access to the organization' }
  ];

  var getPermissionEndpoint = function(repository, entityName, entityKind) {
    if (entityKind == 'robot') {
      entityKind = 'user';
    }

    var namespace = repository.namespace;
    var name = repository.name;
    var url = UtilService.getRestUrl('repository', namespace, name, 'permissions', entityKind, entityName);
    return Restangular.one(url.toString());
  };

  roleService.deleteRepositoryRole = function(repository, entityKind, entityName, callback) {
    if (entityKind == 'robot') {
      entityKind = 'user';
    }

    var errorDisplay = ApiService.errorDisplay('Cannot change permission', function(resp) {
      callback(false);
    });

    var endpoint = getPermissionEndpoint(repository, entityName, entityKind);
    endpoint.customDELETE().then(function() {
      callback(true);
    }, errorDisplay);
  };

  roleService.setRepositoryRole = function(repository, role, entityKind, entityName, callback) {
    if (role == 'none') {
      roleService.deleteRepositoryRole(repository, entityKind, entityName, callback);
      return;
    }

    if (entityKind == 'robot') {
      entityKind = 'user';
    }

    var errorDisplay = ApiService.errorDisplay('Cannot change permission', function(resp) {
      callback(false);
    });

    var permission = {
      'role': role
    };

    var endpoint = getPermissionEndpoint(repository, entityName, entityKind);
    endpoint.customPUT(permission).then(function(resp) {
      callback(true, resp);
    }, errorDisplay);
  };

  roleService.getRepoPermissions = function(namespace, entityKind, entityName, callback) {
    var errorHandler = ApiService.errorDisplay('Could not load permissions', callback);

    if (entityKind == 'team') {
      var params = {
        'orgname': namespace,
        'teamname': entityName
      };

      ApiService.getOrganizationTeamPermissions(null, params).then(function(resp) {
        callback(resp.permissions);
      }, errorHandler);
    } else if (entityKind == 'robot') {
      var parts = entityName.split('+');
      var shortName = parts[1];

      var orgname = UserService.isOrganization(namespace) ? namespace : null;
      ApiService.getRobotPermissions(orgname, null, {'robot_shortname': shortName}).then(function(resp) {
        callback(resp.permissions);
      }, errorHandler);
    } else {
      throw Error('Unknown entity kind ' + entityKind);
    }
  };

  return roleService;
}]);
