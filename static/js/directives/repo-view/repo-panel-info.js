/**
 * An element which displays the information panel for a repository view.
 */
angular.module('quay').directive('repoPanelInfo', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-view/repo-panel-info.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'builds': '=builds',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService, Config, Features, StateService) {
      StateService.updateStateIn($scope, function(state) {
        $scope.inReadOnlyMode = state.inReadOnlyMode;
      });

      $scope.Features = Features;

      $scope.$watch('repository', function(repository) {
        if (!$scope.repository) { return; }

        var namespace = $scope.repository.namespace;
        var name = $scope.repository.name;

        $scope.pullCommand = 'docker pull ' + Config.getDomain() + '/' + namespace + '/' + name;
      });

      $scope.updateDescription = function(content) {
        $scope.repository.description = content;
        $scope.repository.put();
      };

      $scope.getAggregatedUsage = function(stats, days) {
        if (!stats || !stats.length) {
          return 0;
        }

        var count = 0;
        var startDate = moment().subtract(days + 1, 'days');
        for (var i = 0; i < stats.length; ++i) {
          var stat = stats[i];
          var statDate = moment(stat['date']);
          if (statDate.isBefore(startDate)) {
            continue;
          }

          count += stat['count'];
        }
        return count;
      };
    }
  };
  return directiveDefinitionObject;
});
