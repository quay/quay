(function() {
  /**
   * Page to create a new repository.
   */
  angular.module('quayPages').config(['pages', function(pages) {
   pages.create('new-repo', 'new-repo.html', NewRepoCtrl, {
      'newLayout': true,
      'title': 'New Repository',
      'description': 'Create a new Docker repository'
    })
  }]);

  function NewRepoCtrl($scope, $location, $http, $timeout, $routeParams, UserService, ApiService, PlanService, TriggerService, Features) {
    UserService.updateUserIn($scope);

    $scope.Features = Features;
    $scope.TriggerService = TriggerService;

    $scope.repositoryNameRegex = (Features.EXTENDED_REPOSITORY_NAMES) ?
				 new RegExp('^[a-z0-9][.a-z0-9_-]*(\/[a-z0-9][.a-z0-9_-]*)*$') :
				 new RegExp('^[a-z0-9][.a-z0-9_-]*$');

    $scope.repo = {
      'is_public': 0,
      'description': '',
      'initialize': '',
      'name': $routeParams['name'],
      'repo_kind': 'image'
    };

    $scope.changeNamespace = function(namespace) {
      $scope.repo.namespace = namespace;
    };

    $scope.$watch('repo.name', function() {
      $scope.createError = null;
    });

    $scope.startBuild = function() {
      $scope.buildStarting = true;
      $scope.startBuildCallback(function(status, messageOrBuild) {
        if (status) {
          $location.url('/repository/' + $scope.created.namespace + '/' + $scope.created.name +
                        '?tab=builds');
        } else {
          bootbox.alert(messageOrBuild || 'Could not start build');
        }
      });
    };

    $scope.readyForBuild = function(startBuild) {
      $scope.startBuildCallback = startBuild;
    };

    $scope.updateDescription = function(content) {
      $scope.repo.description = content;
    };

    $scope.createNewRepo = function() {
      $scope.creating = true;
      var repo = $scope.repo;
      var data = {
        'namespace': repo.namespace,
        'repository': repo.name,
        'visibility': repo.is_public == '1' ? 'public' : 'private',
        'description': repo.description,
        'repo_kind': repo.repo_kind
      };

      ApiService.createRepo(data).then(function(created) {
        $scope.creating = false;
        $scope.created = created;

        if (repo.repo_kind == 'application') {
          $location.path('/application/' + created.namespace + '/' + created.name);
          return;
        }

        // Start the build if applicable.
        if ($scope.repo.initialize == 'dockerfile' || $scope.repo.initialize == 'zipfile') {
          $scope.createdForBuild = created;
          $scope.startBuild();
          return;
        }

        // Conduct the SCM redirect if applicable.
        var redirectUrl = TriggerService.getRedirectUrl($scope.repo.initialize, repo.namespace, repo.name);
        if (redirectUrl) {
          window.location = redirectUrl;
          return;
        }

        // Otherwise, redirect to the repo page.
        $location.path('/repository/' + created.namespace + '/' + created.name);
      }, function(result) {
        $scope.creating = false;
        $scope.createError = ApiService.getErrorMessage(result);
      });
    };
  }
})();
