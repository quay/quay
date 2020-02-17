/**
 * An element which displays the labels on a repository manifest.
 */
angular.module('quay').directive('manifestLabelList', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/manifest-label-list.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'manifestDigest': '=manifestDigest',
      'cache': '=cache'
    },
    controller: function($scope, $element, ApiService) {
      $scope.labels = null;
      $scope.loadingLabels = false;

      var loadLabels = function() {
        if (!$scope.repository) {
          return;
        }

        if (!$scope.manifestDigest) {
          return;
        }

        if ($scope.cache[$scope.manifestDigest]) {
          $scope.labels = $scope.cache[$scope.manifestDigest];
          return;
        }

        if ($scope.loadingLabels) {
          return;
        }

        $scope.loadingLabels = true;
        $scope.labels = null;
        $scope.loadError = false;

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'manifestref': $scope.manifestDigest
        };

        ApiService.listManifestLabels(null, params).then(function(resp) {
          $scope.labels = resp['labels'];
          $scope.cache[$scope.manifestDigest] = resp['labels'];
          $scope.loadingLabels = false;
        }, function() {
          $scope.loadError = true;
          $scope.loadingLabels = false;
        });
      };

      $scope.$watch('cache', function(cache) {
        if (cache && $scope.manifestDigest && $scope.labels && !cache[$scope.manifestDigest]) {
          loadLabels();
        }
      }, true);

      $scope.$watch('repository', loadLabels);
      $scope.$watch('manifestDigest', loadLabels);
    }
  };
  return directiveDefinitionObject;
});