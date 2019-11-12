/**
 * An element which displays a link to a commit in Git or Mercurial or another source control.
 */
angular.module('quay').directive('sourceCommitLink', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/source-commit-link.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'commitSha': '=commitSha',
      'urlTemplate': '=urlTemplate',
      'showTransclude': '=showTransclude'
    },
    controller: function($scope, $element) {
      $scope.getUrl = function(sha, template) {
        if (!template) { return ''; }
        return template.replace('{sha}', sha);
      };
    }
  };
  return directiveDefinitionObject;
});
