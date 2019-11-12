(function() {
  /**
   * Trigger setup page.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('trigger-setup', 'trigger-setup.html', TriggerSetupCtrl, {
      'title': 'Setup build trigger',
      'description': 'Setup build trigger',
      'newLayout': true
    });
  }]);

  function TriggerSetupCtrl($scope, ApiService, $routeParams, $location, UserService, TriggerService) {
    var namespace = $routeParams.namespace;
    var name = $routeParams.name;
    var trigger_uuid = $routeParams.triggerid;

    var loadRepository = function() {
      var params = {
        'repository': namespace + '/' + name,
        'includeTags': false
      };

      $scope.repositoryResource = ApiService.getRepoAsResource(params).get(function(repo) {
        $scope.repository = repo;
      });
    };

    var loadTrigger = function() {
      var params = {
        'repository': namespace + '/' + name,
        'trigger_uuid': trigger_uuid
      };

      $scope.triggerResource = ApiService.getBuildTriggerAsResource(params).get(function(trigger) {
        $scope.trigger = trigger;
      });
    };

    loadTrigger();
    loadRepository();

    $scope.state = 'managing';

    $scope.activateTrigger = function(event) {
      $scope.state = 'activating';
      var params = {
        'repository': namespace + '/' + name,
        'trigger_uuid': trigger_uuid
      };

      var data = {
        'config': event.config
      };

      if (event.pull_robot) {
        data['pull_robot'] = event.pull_robot['name'];
      }

      var errorHandler = ApiService.errorDisplay('Cannot activate build trigger', function(resp) {
        $scope.state = 'managing';
        return ApiService.getErrorMessage(resp) +
          '\n\nNote: Errors can occur if you do not have admin access on the repository';
      });

      ApiService.activateBuildTrigger(data, params).then(function(resp) {
        $scope.trigger['is_active'] = true;
        $scope.trigger['config'] = resp['config'];
        $scope.trigger['pull_robot'] = resp['pull_robot'];
        $scope.trigger['repository_url'] = resp['repository_url'];
        $scope.state = 'activated';

        // If there are no credentials to display, redirect to the builds tab.
        if (!$scope.trigger['config'].credentials) {
          $location.url('/repository/' + namespace + '/' + name + '?tab=builds');
        }
      }, errorHandler);
    };

    $scope.getTriggerIcon = function() {
      if (!$scope.trigger) { return ''; }
      return TriggerService.getIcon($scope.trigger.service);
    };

    $scope.getTriggerId = function() {
      if (!trigger_uuid) { return ''; }
      return trigger_uuid.split('-')[0];
    };
  }
}());
