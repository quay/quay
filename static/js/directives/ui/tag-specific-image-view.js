/**
 * An element which displays those images which belong to the specified tag *only*. If an image
 * is shared between more than a single tag in the repository, then it is not displayed.
 */
angular.module('quay').directive('tagSpecificImagesView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/tag-specific-images-view.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'repositoryTags': '=repositoryTags',
      'tag': '=tag',
      'imageLoader': '=imageLoader',
      'imageCutoff': '=imageCutoff'
    },
    controller: function($scope, $element, UtilService) {
      $scope.getFirstTextLine = UtilService.getFirstMarkdownLineAsText;
      $scope.loading = false;
      $scope.tagSpecificImages = [];

      $scope.getImageListingClasses = function(image) {
        var classes = '';
        if (!$scope.repositoryTags) {
          return '';
        }

        if (image.ancestors.length > 1) {
          classes += 'child ';
        }

        var currentTag = $scope.repositoryTags[$scope.tag];
        if (currentTag && image.id == currentTag.image_id) {
          classes += 'tag-image ';
        }

        return classes;
      };

      var refresh = function() {
        if (!$scope.repositoryTags || !$scope.tag || !$scope.imageLoader) {
          $scope.tagSpecificImages = [];
          return;
        }

        var tag = $scope.repositoryTags[$scope.tag];
        if (!tag) {
          $scope.tagSpecificImages = [];
          return;
        }

        $scope.loading = true;
        $scope.imageLoader.getTagSpecificImages($scope.tag, function(images) {
          $scope.loading = false;
          $scope.tagSpecificImages = images;
        });
      };

      $scope.$watch('repository', refresh);
      $scope.$watch('repositoryTags', refresh);
      $scope.$watch('tag', refresh);
    }
  };
  return directiveDefinitionObject;
});
