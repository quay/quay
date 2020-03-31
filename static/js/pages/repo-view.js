(function() {
  /**
   * Repository view page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('repo-view', 'repo-view.html', RepoViewCtrl, {
      'newLayout': true,
      'title': '{{ namespace }}/{{ name }}',
      'description': 'Repository {{ namespace }}/{{ name }}'
    });
  }]);

  function RepoViewCtrl($scope, $routeParams, $rootScope, $timeout, ApiService,
                        UserService, AngularPollChannel, UtilService) {
    $scope.namespace = $routeParams.namespace;
    $scope.name = $routeParams.name;

    // Tab-enabled counters.
    $scope.infoShown = 0;
    $scope.tagsShown = 0;
    $scope.logsShown = 0;
    $scope.buildsShown = 0;
    $scope.settingsShown = 0;
    $scope.historyShown = 0;
    $scope.mirrorShown = 0;

    $scope.viewScope = {
      'selectedTags': [],
      'repository': null,
      'builds': null,
      'historyFilter': '',
      'repositoryTags': null,
      'tagsLoading': true
    };

    $scope.repositoryTags = {};

    var buildPollChannel = null;

    // Make sure we track the current user.
    UserService.updateUserIn($scope);

    // Watch the repository to filter any tags removed.
    $scope.$watch('viewScope.repositoryTags', function(repository) {
      if (!repository) { return; }
      $scope.viewScope.selectedTags = filterTags($scope.viewScope.selectedTags);
    });

    var filterTags = function(tags) {
      return (tags || []).filter(function(tag) {
        return !!$scope.viewScope.repositoryTags[tag];
      });
    };

    var loadRepositoryTags = function() {
      loadPaginatedRepositoryTags(1);
      $scope.viewScope.repositoryTags = $scope.repositoryTags;
    };

    var loadPaginatedRepositoryTags = function(page) {
      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'limit': 100,
        'page': page,
        'onlyActiveTags': true
      };

      ApiService.listRepoTags(null, params).then(function(resp) {
        var newTags = resp.tags.reduce(function(result, item, index, array) {
          var tag_name = item['name'];
          result[tag_name] = item;
          return result;
        }, {});

        $.extend($scope.repositoryTags, newTags);

        if (resp.has_additional) {
          loadPaginatedRepositoryTags(page + 1);
        } else {
	  $scope.viewScope.tagsLoading = false;
	}
      });
    };

    var loadRepository = function() {
      // Mark the images to be reloaded.
      $scope.viewScope.images = null;
      loadRepositoryTags();

      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'includeStats': true,
        'includeTags': false
      };

      $scope.repositoryResource = ApiService.getRepoAsResource(params).get(function(repo) {
        if (repo != undefined) {
          $scope.repository = repo;
          $scope.viewScope.repository = repo;

          // Update the page description for SEO
          $rootScope.description = UtilService.getFirstMarkdownLineAsString(repo.description);

          // Load the remainder of the data async, so we don't block the initial view from showing
          $timeout(function() {
            $scope.setTags($routeParams.tag);

            // Track builds.
            buildPollChannel = AngularPollChannel.create($scope, loadRepositoryBuilds, 30000 /* 30s */);
            buildPollChannel.start();
          }, 10);
        }
      });
    };

    var loadRepositoryBuilds = function(callback) {
      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'limit': 3
      };

      var errorHandler = function() {
        callback(false);
      };

      $scope.repositoryBuildsResource = ApiService.getRepoBuildsAsResource(params, /* background */true).get(function(resp) {
        // Note: We could just set the builds here, but that causes a full digest cycle. Therefore,
        // to be more efficient, we do some work here to determine if anything has changed since
        // the last build load in the common case.
        if ($scope.viewScope.builds && resp.builds.length == $scope.viewScope.builds.length) {
          var hasNewInformation = false;
          for (var i = 0; i < resp.builds.length; ++i) {
            var current = $scope.viewScope.builds[i];
            var updated = resp.builds[i];
            if (current.phase != updated.phase || current.id != updated.id) {
              hasNewInformation = true;
              break;
            }
          }

          if (!hasNewInformation) {
            callback(true);
            return;
          }
        }

        $scope.viewScope.builds = resp.builds;
        callback(true);
      }, errorHandler);
    };

    // Load the repository.
    loadRepository();

    $scope.setTags = function(tagNames) {
      if (!tagNames) {
        $scope.viewScope.selectedTags = [];
        return;
      }

      $scope.viewScope.selectedTags = $.unique(tagNames.split(','));
    };

    $scope.showInfo = function() {
      $scope.infoShown++;
    };

    $scope.showBuilds = function() {
      $scope.buildsShown++;
    };

    $scope.showHistory = function() {
      $scope.historyShown++;
    };

    $scope.showSettings = function() {
      $scope.settingsShown++;
    };

    $scope.showMirror = function() {
      $scope.mirrorShown++;
    }

    $scope.showLogs = function() {
      $scope.logsShown++;
    };

    $scope.showTags = function() {
      $timeout(function() {
        $scope.tagsShown = 1;
      }, 10);
    };

    $scope.getImages = function(callback) {
      loadImages(callback);
    };
  }
})();
