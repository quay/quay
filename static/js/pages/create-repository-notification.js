(function() {
  /**
   * Create repository notification page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('create-repository-notification', 'create-repository-notification.html', CreateRepoNotificationCtrl, {
      'newLayout': true,
      'title': 'Create Repo Notification: {{ namespace }}/{{ name }}',
      'description': 'Create repository notification for repository {{ namespace }}/{{ name }}'
    })
  }]);

  function CreateRepoNotificationCtrl($scope, $routeParams, $location, ApiService) {
    $scope.namespace = $routeParams.namespace;
    $scope.name = $routeParams.name;

    var loadRepository = function() {
      var params = {
        'repository': $scope.namespace + '/' + $scope.name,
        'includeTags': false
      };

      $scope.repositoryResource = ApiService.getRepoAsResource(params).get(function(repo) {
        $scope.repository = repo;
      });
    };

    loadRepository();

    $scope.notificationCreated = function() {
      $location.url('repository/' + $scope.namespace + '/' + $scope.name + '?tab=settings');
    };
  }
})();
