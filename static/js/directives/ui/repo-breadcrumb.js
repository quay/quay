/**
 * An element which shows the breadcrumbs for a repository, including subsections such as an
 * an image or a generic subsection.
 */
angular.module('quay').directive('repoBreadcrumb', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-breadcrumb.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repo': '=repo',
      'image': '=image',
      'subsection': '=subsection',
      'subsectionIcon': '=subsectionIcon'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});