/**
 * An element which displays the current status of the service as an announcement bar.
 */
angular.module('quay').directive('quayServiceStatusBar', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/quay-service-status-bar.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {},
    controller: function($scope, $element, StatusService) {
      $scope.indicator = 'loading';

      StatusService.getStatus(function(data) {
        $scope.indicator = data['status']['indicator'];
        $scope.incidents = data['incidents'] || [];
        $scope.scheduled_maintenances = data['scheduled_maintenances'] || [];
      });
    }
  };
  return directiveDefinitionObject;
});