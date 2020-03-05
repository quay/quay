(function() {
  /**
   * Repository listing page. Shows all repositories for all visibile namespaces.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('repo-list', 'repo-list.html', RepoListCtrl, {
      'newLayout': true,
      'title': 'Repositories',
      'description': 'View and manage Docker repositories'
    })
  }]);


  function RepoListCtrl($scope, $sanitize, $q, Restangular, UserService, ApiService, Features,
                        Config, StateService) {
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
            'avatar': org.avatar,
            'public': org.public
          });
        });

        // Load the repos.
        loadStarredRepos();
        loadRepos();
      }
    });

    $scope.isOrganization = function(namespace) {
      return !!UserService.getOrganization(namespace);
    };

    $scope.starToggled = function(repo) {
      if (repo.is_starred) {
        $scope.starred_repositories.value.push(repo);
      } else {
        $scope.starred_repositories.value = $scope.starred_repositories.value.filter(function(repo) {
          return repo.is_starred;
        });
      }
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

    var loadStarredRepos = function() {
      if (!$scope.user || $scope.user.anonymous) {
        return;
      }

      var options = {
        'starred': true,
        'last_modified': true,
        'popularity': true
      };

      $scope.starred_repositories = ApiService.listReposAsResource().withOptions(options).get(function(resp) {
        return resp.repositories.map(function(repo) {
          repo = findDuplicateRepo(repo);
          repo.is_starred = true;
          return repo;
        });
      });
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
          'public': namespace.public
        };

        namespace.repositories = ApiService.listReposAsResource().withPagination('repositories').withOptions(options).get(function(resp) {
          return resp.repositories.map(findDuplicateRepo);
        });

        $scope.resources.push(namespace.repositories);
      });
    };
  }
})();
