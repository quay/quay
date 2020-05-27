(function() {
  /**
   * Search page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('search', 'search.html', SearchCtrl, {
      'title': 'Search'
    });
  }]);

  function SearchCtrl($scope, ApiService, $routeParams, $location, Config) {
    var refreshResults = function() {
      $scope.currentPage = ($routeParams['page'] || '1') * 1;

      var params = {
        'query': $routeParams['q'],
        'page': $scope.currentPage,
        'includeUsage': true
      };

      var MAX_PAGE_RESULTS = Config['SEARCH_MAX_RESULT_PAGE_COUNT'];
      var page = $routeParams['page'] || 1;

      $scope.maxPopularity = 0;
      $scope.resultsResource = ApiService.conductRepoSearchAsResource(params).get(function(resp) {
        $scope.results = resp['results'];
        // Only show "Next Page" if we have more results, and we aren't on the max page
        $scope.showNextButton = page < MAX_PAGE_RESULTS && resp['has_additional'];
        // Show some help text if we're on the last page, making them specify the search more
        $scope.showMaxResultsHelpText = page >= MAX_PAGE_RESULTS;
        $scope.startIndex = resp['start_index'];
        resp['results'].forEach(function(result) {
          $scope.maxPopularity = Math.max($scope.maxPopularity, result['popularity']);
        });
      });
    };

    $scope.previousPage = function() {
      $location.search('page', (($routeParams['page'] || 1) * 1) - 1);
    };

    $scope.nextPage = function() {
      $location.search('page', (($routeParams['page'] || 1) * 1) + 1);
    };

    $scope.currentQuery = $routeParams['q'];
    refreshResults();

    $scope.$on('$routeUpdate', function(){
      $scope.currentQuery = $routeParams['q'];
      refreshResults();
    });
  }

  SearchCtrl.$inject = ['$scope', 'ApiService', '$routeParams', '$location', 'Config'];
})();