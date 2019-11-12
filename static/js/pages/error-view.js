(function() {
  /**
   * Error view page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('error-view', 'error-view.html', ErrorViewCtrl, {
      'title': '{{info.error_message || "Error"}}',
      'description': 'Error',
      'newLayout': false
    });
  }]);

  function ErrorViewCtrl($scope, ApiService, $routeParams, $rootScope, UserService) {
    $scope.info = window.__error_info;
    $scope.code = window.__error_code || 404;
  }
}());