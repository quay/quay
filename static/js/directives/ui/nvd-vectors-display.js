/**
 * An element which displays NVD vectors is an expanded format.
 */
angular.module('quay').directive('nvdVectorsDisplay', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/nvd-vectors-display.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'vectors': '@vectors',
    },
    controller: function($scope, $element, VulnerabilityService) {
      $scope.parsedVectors = VulnerabilityService.parseVectorsString($scope.vectors);

      $scope.getVectorTitle = function(vector) {
        return VulnerabilityService.getVectorTitle(vector);
      };

      $scope.getVectorDescription = function(vector) {
        return VulnerabilityService.getVectorDescription(vector);
      };

      $scope.getVectorOptions = function(vectorString) {
        return VulnerabilityService.getVectorOptions(vectorString);
      };

      $scope.getVectorClasses = function(option, vectorString) {
        return VulnerabilityService.getVectorClasses(option, vectorString);
      };
    }
  };
  return directiveDefinitionObject;
});