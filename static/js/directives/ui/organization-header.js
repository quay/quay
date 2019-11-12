/**
 * An element which displays an organization header, optionally with trancluded content.
 */
angular.module('quay').directive('organizationHeader', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/organization-header.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'organization': '=organization',
      'teamName': '=teamName',
      'clickable': '=clickable'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});