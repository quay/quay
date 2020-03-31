/**
 * An element which displays the features of a manifest.
 */
angular.module('quay').directive('manifestFeatureView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/manifest-feature-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'manifest': '=manifest',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, Config, ApiService, VulnerabilityService, ViewArray, TableService) {
      $scope.options = {
        'filter': null,
        'predicate': 'fixableScore',
        'reverse': false,
      };

      $scope.TableService = TableService;
      $scope.loading = false;

      var buildOrderedFeatures = function() {
        if (!$scope.featuresInfo) {
          return;
        }

        var features = $scope.featuresInfo.features;
        $scope.orderedFeatures = TableService.buildOrderedItems(features, $scope.options,
            ['name', 'version', 'imageId'],
            ['score', 'fixableScore', 'leftoverScore'])
      };

      var buildChart = function() {
        var chartData = $scope.featuresInfo.severityBreakdown;
        var colors = [];
        for (var i = 0; i < chartData.length; ++i) {
          colors.push(chartData[i].color);
        }

        nv.addGraph(function() {
          var chart = nv.models.pieChart()
              .x(function(d) { return d.label })
              .y(function(d) { return d.value })
              .margin({left: -10, right: -10, top: -10, bottom: -10})
              .showLegend(false)
              .showLabels(true)
              .labelThreshold(.05)
              .labelType("percent")
              .donut(true)
              .color(colors)
              .donutRatio(0.5);

            d3.select("#featureDonutChart svg")
                .datum(chartData)
                .transition()
                .duration(350)
                .call(chart);

          return chart;
        });
      };

      var loadManifestVulnerabilities = function() {
        if ($scope.loading) {
          return;
        }

        $scope.loading = true;
        VulnerabilityService.loadManifestVulnerabilities($scope.repository, $scope.manifest.digest, function(resp) {
          $scope.securityStatus = resp.status;
          $scope.featuresInfo = VulnerabilityService.buildFeaturesInfo($scope.manifest, resp);

          buildOrderedFeatures();
          buildChart();
          return resp;
        }, function() {
          $scope.securityStatus = 'error';
        });
      };

      $scope.$watch('options.predicate', buildOrderedFeatures);
      $scope.$watch('options.reverse', buildOrderedFeatures);
      $scope.$watch('options.filter', buildOrderedFeatures);

      $scope.$watch('repository', function(repository) {
        if ($scope.isEnabled && $scope.repository && $scope.manifest) {
          loadManifestVulnerabilities();
        }
      });

      $scope.$watch('manifest', function(manifest) {
        if ($scope.isEnabled && $scope.repository && $scope.manifest) {
          loadManifestVulnerabilities();
        }
      });

      $scope.$watch('isEnabled', function(isEnabled) {
        if ($scope.isEnabled && $scope.repository && $scope.manifest) {
          loadManifestVulnerabilities();
        }
      });
    }
  };
  return directiveDefinitionObject;
});