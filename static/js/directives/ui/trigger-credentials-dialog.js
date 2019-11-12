/**
 * An element which displays a dialog with the necessary credentials for a build trigger.
 */
angular.module('quay').directive('triggerCredentialsDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/trigger-credentials-dialog.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'trigger': '=trigger',
      'counter': '=counter'
    },
    controller: function($scope, $element) {
      var show = function() {
        if (!$scope.trigger || !$scope.counter) {
          $('#triggercredentialsmodal').modal('hide');
          return;
        }
        $('#triggercredentialsmodal').modal({});
      };

      $scope.$watch('trigger', show);
      $scope.$watch('counter', show);
    }
  };
  return directiveDefinitionObject;
});
