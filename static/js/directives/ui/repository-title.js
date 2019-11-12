/**
 * An element which displays the title of a repository (either 'repository' or 'application').
 */
angular.module('quay').directive('repositoryTitle', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repository-title.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '<repository'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});