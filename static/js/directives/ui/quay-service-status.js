/**
 * An element which displays the current status of the service.
 */
angular.module('quay').directive('quayServiceStatus', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/quay-service-status.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {},
    controller: function($scope, $element, StatusService) {
      $scope.indicator = 'loading';
      $scope.description = '';

      StatusService.getStatus(function(data) {
        $scope.indicator = data['status']['indicator'];
        $scope.incidents = data['incidents'];
        $scope.description = data['status']['description'];
        $scope.degraded = [];

        data['components'].forEach(function(component, index) {
          if (component.status != 'operational') {
            $scope.degraded.push(component);
          }
        });
      });
    }
  };
  return directiveDefinitionObject;
});