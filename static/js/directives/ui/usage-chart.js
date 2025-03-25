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
      'marketplaceTotal': '=marketplaceTotal',
      'limit': '=limit',
      'usageTitle': '@usageTitle'
    },
    controller: function($scope, $element) {
      if($scope.subscribedPlan !== undefined){
        $scope.total = $scope.subscribedPlan.privateRepos || 0;
      }
      else {
        $scope.total = 0;
      }
      $scope.limit = "";

      var chart = null;

      var update = function() {
        if (!chart) {
          chart = new UsageChart();
          chart.draw('usage-chart-element');
        }

        var current = $scope.current || 0;
        var total = $scope.total + $scope.marketplaceTotal;
        if (current > total) {
          $scope.limit = 'over';
        } else if (current == total) {
          $scope.limit = 'at';
        } else if (current >= total * 0.7) {
          $scope.limit = 'near';
        } else {
          $scope.limit = 'none';
        }

        var finalAmount = $scope.total + $scope.marketplaceTotal;
        if(finalAmount >= 9223372036854775807) { finalAmount = "inf"; }
        chart.update($scope.current, finalAmount);
      };

      $scope.$watch('current', update);
      $scope.$watch('total', update);
      $scope.$watch('marketplaceTotal', update);
    }
  };
  return directiveDefinitionObject;
});
