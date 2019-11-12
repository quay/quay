(function() {
  /**
   * Application view page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('app-view', 'app-view.html', AppViewCtrl, {
      'newLayout': true,
      'title': '{{ namespace }}/{{ name }}',
      'description': 'Application {{ namespace }}/{{ name }}'
    });
  }]);

  function AppViewCtrl($scope, $routeParams, $rootScope, ApiService, UtilService) {
    $scope.namespace = $routeParams.namespace;
    $scope.name = $routeParams.name;

    $scope.viewScope = {};
    $scope.settingsShown = 0;

    $scope.showSettings = function() {
      $scope.settingsShown++;
    };

    var loadRepository = function() {
      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'repo_kind': 'application',
        'includeStats': true,
        'includeTags': false
      };

      $scope.repositoryResource = ApiService.getRepoAsResource(params).get(function(repo) {
        if (repo != undefined) {
          $scope.repository = repo;
          $scope.viewScope.repository = repo;

          // Update the page description for SEO
          $rootScope.description = UtilService.getFirstMarkdownLineAsString(repo.description);
        }
      });
    };

    loadRepository();
  }
})();
