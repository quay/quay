/**
 * An element for managing global messages.
 */
angular.module('quay').directive('superUserBuildLogs', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/super-user-build-logs.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'isEnabled': '=isEnabled'
    },
    controller: function ($scope, $element, ApiService) {
      $scope.buildParams = {};
      $scope.showLogTimestamps = true;
      $scope.buildId = null;

      $scope.loadBuild = function () {
        var params = {
          'build_uuid': $scope.buildParams.buildUuid
        };

        $scope.buildId = $scope.buildParams.buildUuid;
        $scope.buildResource = ApiService.getRepoBuildSuperUserAsResource(params).get(function (build) {
          $scope.build = build;
        });
      };
    }
  };
  return directiveDefinitionObject;
});
