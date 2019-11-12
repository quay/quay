/**
 * An element which displays a dialog for manually trigger a build.
 */
angular.module('quay').directive('manualTriggerBuildDialog', function () {
  var directiveDefinitionObject = {
    templateUrl: '/static/directives/manual-trigger-build-dialog.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'counter': '=counter',
      'trigger': '=trigger',
      'buildStarted': '&buildStarted'
    },
    controller: function($scope, $element, ApiService, TriggerService) {
      $scope.parameters = {};
      $scope.fieldOptions = {};
      $scope.lookaheadItems = {};

      $scope.startTrigger = function() {
        $element.find('.startTriggerDialog').modal('hide');
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'trigger_uuid': $scope.trigger.id
        };

        ApiService.manuallyStartBuildTrigger($scope.parameters || {}, params).then(function(resp) {
          $scope.buildStarted({
            'trigger': $scope.trigger,
            'parameters': $scope.parameters,
            'build': resp
          });
        }, ApiService.errorDisplay('Could not start build'));
      };

      $scope.show = function() {
        $scope.parameters = {};
        $scope.fieldOptions = {};

        var parameters = TriggerService.getRunParameters($scope.trigger.service);
        for (var i = 0; i < parameters.length; ++i) {
          var parameter = parameters[i];
          if (parameter['type'] == 'option' || parameter['type'] == 'autocomplete') {
            // Load the values for this parameter.
            var params = {
              'repository': $scope.repository.namespace + '/' + $scope.repository.name,
              'trigger_uuid': $scope.trigger.id,
              'field_name': parameter['name']
            };

            ApiService.listTriggerFieldValues(null, params).then(function(resp) {
              $scope.fieldOptions[parameter['name']] = resp['values'];
            });
          }

          delete $scope.parameters[parameter['name']];
        }

        $scope.runParameters = parameters;
        $element.find('.startTriggerDialog').modal('show');
      };

      $scope.$watch('counter', function(counter) {
        if (counter) {
          $scope.show();
        }
      });
    }
  };
  return directiveDefinitionObject;
});
