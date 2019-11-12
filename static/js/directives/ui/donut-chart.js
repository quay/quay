/**
 * An element which displays a donut chart of data.
 */
angular.module('quay').directive('donutChart', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/donut-chart.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'width': '@width',
      'minPercent': '@minPercent',
      'data': '=data',
    },
    controller: function($scope, $element) {
      $scope.created = false;

      // Based on: http://bl.ocks.org/erichoco/6694616
      var chart = d3.select($element.find('.donut-chart-element')[0]);

      var renderChart = function() {
        if (!$scope.data || !$scope.data.length) {
          return;
        }

        // Adjust the data to make sure each non-zero entry is at minimum. While technically
        // not accurate, it will make the section visible to the user.
        var adjustedData = []
        var total = 0;
        $scope.data.map(function(entry) {
          total += entry.value;
        });

        adjustedData = $scope.data.map(function(entry) {
          var value = entry.value;
          if ($scope.minPercent) {
            if (value / total < $scope.minPercent / 100) {
              value = total * $scope.minPercent / 100;
            }
          }

          var copy =  $.extend({}, entry);
          copy.value = value;
          return copy;
        });


        var $chart = $element.find('.donut-chart-element');
        $chart.empty();

        var width = $scope.width * 1;
        var chart_m = width / 2 * 0.14;
        var chart_r = width / 2 * 0.85;

        var topG = chart.append('svg:svg')
                            .attr('width', (chart_r + chart_m) * 2)
                            .attr('height', (chart_r + chart_m) * 2)
                            .append('svg:g')
                                .attr('class', 'donut')
                                .attr('transform', 'translate(' + (chart_r + chart_m) + ',' +
                                                   (chart_r + chart_m) + ')');


        var arc = d3.svg.arc()
                        .innerRadius(chart_r * 0.6)
                        .outerRadius(function(d, i) {
                          return i == adjustedData.length - 1 ? chart_r * 1.2 : chart_r * 1;
                        });

        var pie = d3.layout.pie()
                           .sort(null)
                           .value(function(d) {
                              return d.value;
                           });

        var reversed = adjustedData.reverse();
        var g = topG.selectAll(".arc")
                    .data(pie(reversed))
                    .enter().append("g")
                      .attr("class", "arc");

        g.append("path")
            .attr("d", arc)
            .style('stroke', '#fff')
            .style("fill", function(d) { return d.data.color; });

      };

      $scope.$watch('data', renderChart);
    }
  };
  return directiveDefinitionObject;
});