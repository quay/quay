import { UsageChart } from '../../graphing';


/**
 * An element which displays a donut chart, along with warnings if the limit is close to being
 * reached.
 */
angular.module('quay').directive('usageChart', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/usage-chart.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'current': '=current',
      'total': '=total',
      'limit': '=limit',
      'usageTitle': '@usageTitle'
    },
    controller: function($scope, $element) {
      $scope.limit = "";

      var chart = null;

      var update = function() {
        if ($scope.current == null || $scope.total == null) { return; }
        if (!chart) {
          chart = new UsageChart();
          chart.draw('usage-chart-element');
        }

        var current = $scope.current || 0;
        var total = $scope.total || 0;
        if (current > total) {
          $scope.limit = 'over';
        } else if (current == total) {
          $scope.limit = 'at';
        } else if (current >= total * 0.7) {
          $scope.limit = 'near';
        } else {
          $scope.limit = 'none';
        }

        chart.update($scope.current, $scope.total);
      };

      $scope.$watch('current', update);
      $scope.$watch('total', update);
    }
  };
  return directiveDefinitionObject;
});
