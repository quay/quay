/**
 * An element which displays a progressbar for the given build.
 */
angular.module('quay').directive('buildProgress', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-progress.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build'
    },
    controller: function($scope, $element) {
      $scope.getPercentage = function(buildInfo) {
        switch (buildInfo.phase) {
          case 'pulling':
            return buildInfo.status.pull_completion * 100;
            break;

          case 'building':
            return (buildInfo.status.current_command / buildInfo.status.total_commands) * 100;
            break;

          case 'pushing':
            return buildInfo.status.push_completion * 100;
            break;

          case 'priming-cache':
            return buildInfo.status.cache_completion * 100;
            break;

          case 'complete':
            return 100;
            break;

          case 'initializing':
          case 'checking-cache':
          case 'starting':
          case 'waiting':
          case 'cannot_load':
          case 'unpacking':
            return 0;
            break;
        }

        return -1;
      };
    }
  };
  return directiveDefinitionObject;
});

