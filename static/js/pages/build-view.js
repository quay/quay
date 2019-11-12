(function() {
  /**
   * Build view page. Displays the view of a particular build for a repository.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('build-view', 'build-view.html', BuildViewCtrl, {
      newLayout: true,
      title: 'Build {{ build.display_name }}',
      description: 'Logs and status for build {{ build.display_name }}'
    });
  }]);

  function BuildViewCtrl($scope, ApiService, $routeParams, AngularPollChannel, CookieService,
                         $location, StateService) {
    $scope.inReadOnlyMode = StateService.inReadOnlyMode();
    $scope.namespace = $routeParams.namespace;
    $scope.name = $routeParams.name;
    $scope.build_uuid = $routeParams.buildid;

    if (!CookieService.get('quay.showBuildLogTimestamps')) {
      $scope.showLogTimestamps = true;
    } else {
      $scope.showLogTimestamps = CookieService.get('quay.showBuildLogTimestamps') == 'true';
    }

    var loadBuild = function() {
      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'build_uuid': $scope.build_uuid
      };

      $scope.buildResource = ApiService.getRepoBuildAsResource(params).get(function(build) {
        $scope.build = build;
        $scope.originalBuild = build;
      });
    };

    var loadRepository = function() {
      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'includeTags': false
      };

      $scope.repoResource = ApiService.getRepoAsResource(params).get(function(repo) {
        $scope.repo = repo;
      }, ApiService.errorDisplay('Cannot load repository'));
    };

    // Page startup:
    loadRepository();
    loadBuild();

    $scope.askCancelBuild = function(build) {
      bootbox.confirm('Are you sure you want to cancel this build?', function(r) {
        if (r) {
          var params = {
            'repository': $scope.namespace + '/' + $scope.name,
            'build_uuid': build.id
          };

          ApiService.cancelRepoBuild(null, params).then(function () {
            $location.path('/repository/' + $scope.namespace + '/' + $scope.name);

          }, ApiService.errorDisplay('Cannot cancel build'));
        }
      });
    };

    $scope.toggleTimestamps = function() {
      $scope.showLogTimestamps = !$scope.showLogTimestamps;
      CookieService.putPermanent('quay.showBuildLogTimestamps', $scope.showLogTimestamps);
    };

    $scope.setUpdatedBuild = function(build) {
      $scope.build = build;
    };
  }
})();
