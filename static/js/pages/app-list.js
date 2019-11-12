(function() {
  /**
   * Application listing page. Shows all applications for all visibile namespaces.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('app-list', 'app-list.html', AppListCtrl, {
      'newLayout': true,
      'title': 'Applications',
      'description': 'View and manage applications'
    })
  }]);

  function AppListCtrl($scope, $sanitize, $q, Restangular, UserService, ApiService, Features,
                       StateService) {
    $scope.namespace = null;
    $scope.page = 1;
    $scope.publicPageCount = null;
    $scope.allRepositories = {};
    $scope.loading = true;
    $scope.resources = [];
    $scope.Features = Features;
    $scope.inReadOnlyMode = StateService.inReadOnlyMode();

    // When loading the UserService, if the user is logged in, create a list of
    // relevant namespaces and collect the relevant repositories.
    UserService.updateUserIn($scope, function(user) {
      $scope.loading = false;
      if (!user.anonymous) {
        // Add our user to our list of namespaces.
        $scope.namespaces = [{
          'name': user.username,
          'avatar': user.avatar
        }];

        // Add each org to our list of namespaces.
        user.organizations.map(function(org) {
          $scope.namespaces.push({
            'name': org.name,
            'avatar': org.avatar
          });
        });

        // Load the repos.
        loadRepos();
      }
    });

    $scope.isOrganization = function(namespace) {
      return !!UserService.getOrganization(namespace);
    };

    // Finds a duplicate repo if it exists. If it doesn't, inserts the repo.
    var findDuplicateRepo = function(repo) {
      var found = $scope.allRepositories[repo.namespace + '/' + repo.name];
      if (found) {
        return found;
      } else {
        $scope.allRepositories[repo.namespace + '/' + repo.name] = repo;
        return repo;
      }
    };

    var loadRepos = function() {
      if (!$scope.user || $scope.user.anonymous || $scope.namespaces.length == 0) {
        return;
      }

      $scope.namespaces.map(function(namespace) {
        var options = {
          'namespace': namespace.name,
          'last_modified': true,
          'popularity': true,
          'repo_kind': 'application',
          'public': true,
        };

        namespace.repositories = ApiService.listReposAsResource().withOptions(options).get(function(resp) {
          return resp.repositories.map(findDuplicateRepo);
        });

        $scope.resources.push(namespace.repositories);
      });
    };
  }
})();
