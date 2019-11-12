/**
 * An element which displays a date+count heatmap.
 */
angular.module('quay').directive('heatmap', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/heatmap.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'data': '=data',
      'startCount': '@startCount',
      'startDomain': '@startDomain',

      'itemName': '@itemName',
      'domain': '@domain',
      'range': '@range'
    },
    controller: function($scope, $element, $timeout) {
      var cal = null;

      var refresh = function() {
        var data = $scope.data;
        if (!data) { return; }

        if (!cal) {
          var start = moment().add($scope.startCount * 1, $scope.startDomain).toDate();
          var highlight = [];
          for (i = 0; i < 31; ++i) {
            var d = moment().add('day', i).toDate();
            highlight.push(d);
          }

          cal = new CalHeatMap();
          cal.init({
            itemName: $scope.itemName,
            domain: $scope.domain,
            range: $scope.range * 1,

            start: start,
            itemSelector: $element.find('.heatmap-element')[0],
            cellSize: 15,
            domainMargin: [10, 10, 10, 10],
            displayLegend: false,
            tooltip: true,
            weekStartOnMonday: false,
            highlight: highlight,
            legendColors: {
              empty: "#f4f4f4",
              min: "#c9e9fb",
              max: "steelblue",
              base: 'white'
            }
          });
        }

        var formatted = formatData(data);
        cal.update(formatted.data);
        cal.setLegend(formatted.legendDomain);
      };

      var formatData = function(data) {
        var timestamps = {};
        var max = 1;
        data.forEach(function(entry) {
          timestamps[moment(entry.date).unix()] = entry.count;
          max = Math.max(max, entry.count);
        });

        var domain = [];
        var current = 1;
        for (var i = 0; i < 4; ++i) {
          domain.push(current);
          current += max / 5;
        }

        return {
          data: timestamps,
          legendDomain: domain
        };
      };

      $scope.$watch('data', function() {
        $timeout(refresh, 750);
      });
    }
  };
  return directiveDefinitionObject;
});