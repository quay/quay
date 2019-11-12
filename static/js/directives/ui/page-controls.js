/**
 * An element which displays controls for moving between pages of paginated results.
 */
angular.module('quay').directive('pageControls', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/page-controls.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'currentPage': '=currentPage',
      'pageSize': '=pageSize',
      'totalCount': '=totalCount'
    },
    controller: function($scope, $element) {
      $scope.getPageStart = function(currentPage, pageSize, totalCount) {
        return Math.min((currentPage * pageSize) + 1, totalCount);
      };

      $scope.getPageEnd = function(currentPage, pageSize, totalCount) {
        return Math.min(((currentPage + 1) * pageSize), totalCount);
      };

      $scope.getPageCount = function(pageSize, totalCount) {
        return Math.ceil(totalCount / pageSize);
      };

      $scope.changePage = function(offset) {
        $scope.currentPage += offset;
        $scope.currentPage = Math.max($scope.currentPage, 0);
        $scope.currentPage = Math.min($scope.currentPage, $scope.getPageCount($scope.pageSize, $scope.totalCount));
      };

      $scope.setPage = function(page) {
        $scope.currentPage = page;
      };
    }
  };
  return directiveDefinitionObject;
});