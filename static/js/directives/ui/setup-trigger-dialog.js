/**
 * An element which displays a dialog for setting up a build trigger.
 */
angular.module('quay').directive('setupTriggerDialog', function () {
  var directiveDefinitionObject = {
    templateUrl: '/static/directives/setup-trigger-dialog.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'trigger': '=trigger',
      'counter': '=counter',
      'canceled': '&canceled',
      'activated': '&activated',
      'triggerRunner': '&triggerRunner'
    },
    controller: function($scope, $element, ApiService, UserService, TriggerService) {
      var modalSetup = false;

      $scope.state = {};
      $scope.nextStepCounter = -1;
      $scope.currentView = 'config';
      $scope.TriggerService = TriggerService

      $scope.show = function() {
        if (!$scope.trigger || !$scope.repository) { return; }

        $scope.currentView = 'config';
        $('#setupTriggerModal').modal({});

        if (!modalSetup) {
          $('#setupTriggerModal').on('hidden.bs.modal', function () {
            if (!$scope.trigger || $scope.trigger['is_active']) { return; }

            $scope.nextStepCounter = -1;
            $scope.$apply(function() {
              $scope.cancelSetupTrigger();
            });
          });

          modalSetup = true;
          $scope.nextStepCounter = 0;
        }
      };

      $scope.isNamespaceAdmin = function(namespace) {
        return UserService.isNamespaceAdmin(namespace);
      };

      $scope.cancelSetupTrigger = function() {
        $scope.canceled({'trigger': $scope.trigger});
      };

      $scope.hide = function() {
        $('#setupTriggerModal').modal('hide');
      };

      $scope.runTriggerNow = function() {
        $('#setupTriggerModal').modal('hide');
        $scope.triggerRunner({'trigger': $scope.trigger});
      };

      $scope.checkAnalyze = function(isValid) {
        $scope.currentView = 'analyzing';
        $scope.pullInfo = {
          'is_public': true
        };

        if (!isValid) {
          $scope.currentView = 'analyzed';
          return;
        }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'trigger_uuid': $scope.trigger.id
        };

        var data = {
          'config': $scope.trigger.config
        };

        ApiService.analyzeBuildTrigger(data, params).then(function(resp) {
          $scope.currentView = 'analyzed';

          if (resp['status'] == 'analyzed') {
            if (resp['robots'] && resp['robots'].length > 0) {
              $scope.pullInfo['pull_entity'] = resp['robots'][0];
             } else {
              $scope.pullInfo['pull_entity'] = null;
            }

            $scope.pullInfo['is_public'] = false;
          }

          $scope.pullInfo['analysis'] = resp;
        }, ApiService.errorDisplay('Cannot load Dockerfile information'));
      };

      $scope.activate = function() {
        if (!$scope.trigger) {
          return;
        }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'trigger_uuid': $scope.trigger.id
        };

        var data = {
          'config': $scope.trigger['config']
        };

        if ($scope.pullInfo['pull_entity']) {
          data['pull_robot'] = $scope.pullInfo['pull_entity']['name'];
        }

        $scope.currentView = 'activating';

        var errorHandler = ApiService.errorDisplay('Cannot activate build trigger', function(resp) {
          $scope.hide();
          $scope.canceled({'trigger': $scope.trigger});

          return ApiService.getErrorMessage(resp) +
            '\n\nNote: Errors can occur if you do not have admin access on the repository.';
        });

        ApiService.activateBuildTrigger(data, params).then(function(resp) {
          if (!$scope.trigger) {
            return;
          }

          $scope.trigger['is_active'] = true;
          $scope.trigger['config'] = resp['config'];
          $scope.trigger['pull_robot'] = resp['pull_robot'];
          $scope.trigger['repository_url'] = resp['repository_url'];
          $scope.activated({'trigger': $scope.trigger});
          $scope.currentView = 'postActivation';
        }, errorHandler);
      };

      var check = function() {
        if ($scope.counter && $scope.trigger && $scope.repository) {
          $scope.show();
        }
      };

      $scope.$watch('trigger', check);
      $scope.$watch('counter', check);
      $scope.$watch('repository', check);
    }
  };
  return directiveDefinitionObject;
});

