/**
 * An element which displays a table for setting permissions for an entity to repositories under
 * a namespace.
 */
angular.module('quay').directive('setRepoPermissions', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/set-repo-permissions.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'namespace': '=namespace',
      'entityName': '=entityName',
      'entityKind': '=entityKind',

      'setPermissions': '=setPermissions',

      'hasCheckedRepositories': '=hasCheckedRepositories',
      'hasChangedRepositories': '=hasChangedRepositories',

      'repositoriesLoaded': '&repositoriesLoaded',
      'settingPermissions': '&settingPermissions',
      'permissionsSet': '&permissionsSet',
    },

    controller: function($scope, $element, ApiService, UIService, TableService, RolesService, UserService) {
      $scope.TableService = TableService;

      $scope.options = {
        'predicate': 'last_modified_datetime',
        'reverse': false,
        'filter': ''
      };

      $scope.repositories = null;
      $scope.currentNamespace = null;
      $scope.currentEntityName = null;

      var checkForChanges = function() {
        var hasChanges = false;
        if (!$scope.repositories) {
          return;
        }

        $scope.repositories.forEach(function(repo) {
          if (repo['permission'] != repo['original_permission']) {
            hasChanges = true;
          }
        });

        $scope.hasCheckedRepositories = !!$scope.checkedRepos.checked.length;
        $scope.hasChangedRepositories = hasChanges;
      };

      var handleRepoCheckChange = function() {
        if (!$scope.repositories) {
          return;
        }
        $scope.repositories.forEach(function(repo) {
          if ($scope.checkedRepos.isChecked(repo)) {
            if (repo['permission'] == 'none') {
              repo['permission'] = 'read';
            }
          } else {
            repo['permission'] = 'none';
          }
        });

        checkForChanges();
      };

      var setRepoState = function() {
        if (!$scope.repositories) {
          return;
        }

        $scope.orderedRepositories = TableService.buildOrderedItems(
            $scope.repositories, $scope.options,
            ['name', 'permission'],
            ['last_modified_datetime']);
      };

      var loadRepositoriesAndPermissions = function() {
        if (!$scope.namespace || !$scope.entityName || !$scope.entityKind) {
          return;
        }

        if (($scope.entityName == $scope.currentEntityName) &&
            ($scope.namespace == $scope.currentNamespace)) {
          return;
        }

        $scope.currentNamespace = $scope.namespace;
        $scope.currentEntityName = $scope.entityName;

        // Load the repository permissions for the entity first. We then load the full repo list
        // and compare.
        RolesService.getRepoPermissions($scope.namespace, $scope.entityKind, $scope.entityName,
          function(permissions) {
            if (permissions == null) {
              $scope.currentNamespace = null;
              $scope.currentEntityName = null;
              return;
            }

            var existingPermissionsMap = {};
            permissions.forEach(function(existingPermission) {
              existingPermissionsMap[existingPermission.repository.name] = existingPermission.role;
            });

            loadRepositories(existingPermissionsMap);
          });
      };

      var loadRepositories = function(existingPermissionsMap) {
        $scope.namespaceInfo = UserService.getNamespace($scope.namespace);

        // Load the repositories under the entity's namespace, along with the current repo
        // permissions for the entity.
        var params = {
          'namespace': $scope.namespace,
          'last_modified': true
        };

        ApiService.listRepos(null, params).then(function(resp) {
          $scope.currentNamespace = $scope.namespace;

          var repos = [];
          if (!resp || !resp['repositories'] || resp['repositories'].length == 0) {
            $scope.repositoriesLoaded({'repositories': []});
            return;
          }

          resp['repositories'].forEach(function(repo) {
            var existingPermission = existingPermissionsMap[repo.name] || 'none';

            repos.push({
              'namespace': repo.namespace,
              'name': repo.name,
              'last_modified': repo.last_modified,
              'last_modified_datetime': TableService.getReversedTimestamp(repo.last_modified),
              'permission': existingPermission,
              'original_permission': existingPermission
            });
          });

          $scope.repositories = repos;
          $scope.checkedRepos = UIService.createCheckStateController($scope.repositories, 'name');

          repos.forEach(function(repo) {
            if (repo.permission != 'none') {
              $scope.checkedRepos.checkItem(repo);
            }
          });

          $scope.checkedRepos.listen(handleRepoCheckChange);

          setRepoState();
          $scope.repositoriesLoaded({'repositories': repos});
        }, ApiService.errorDisplay('Could not load repositories'));
      };

      var setPermissions = function() {
        if (!$scope.checkedRepos || !$scope.namespace || !$scope.repositories) {
          return;
        }

        $scope.settingPermissions();

        var repos = $scope.repositories;
        var counter = 0;

        var setPerm = function() {
          if (counter >= repos.length) {
            $scope.permissionsSet({'repositories': $scope.checkedRepos.checked});
            $scope.checkedRepos.setChecked([]);
            return;
          }

          var repo = repos[counter];
          if (repo['permission'] == repo['original_permission']) {
            // Skip changing it.
            counter++;
            setPerm();
            return;
          }

          RolesService.setRepositoryRole(repo, repo.permission, $scope.entityKind,
                                         $scope.entityName, function(status) {
            if (status) {
              counter++;
              setPerm();
            }
          });
        };

        setPerm();
      };

      $scope.setRole = function(role, repo) {
        repo['permission'] = role;

        if (role == 'none') {
          $scope.checkedRepos.uncheckItem(repo);
        } else {
          $scope.checkedRepos.checkItem(repo);
        }

        checkForChanges();
      };

      $scope.allRepositoriesFilter = function(item) {
        return true;
      };

      $scope.noRepositoriesFilter = function(item) {
        return false;
      };

      $scope.missingPermsRepositoriesFilter = function(item) {
        return !item.perm;
      };

      $scope.$watch('options.predicate', setRepoState);
      $scope.$watch('options.reverse', setRepoState);
      $scope.$watch('options.filter', setRepoState);

      $scope.$watch('namespace', loadRepositoriesAndPermissions);
      $scope.$watch('entityName', loadRepositoriesAndPermissions);
      $scope.$watch('entityKind', loadRepositoriesAndPermissions);

      $scope.$watch('setPermissions', function(value) {
        if (value) {
          setPermissions();
        }
      });
    }
  };
  return directiveDefinitionObject;
});
