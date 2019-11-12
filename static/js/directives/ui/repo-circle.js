/**
 * An element which shows a repository icon (inside a circle).
 */
angular.module('quay').directive('repoCircle', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-circle.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repo': '=repo'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});
