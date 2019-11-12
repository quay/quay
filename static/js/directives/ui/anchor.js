/**
 * An element which displays its contents wrapped in an <a> tag, but only if the href is not null.
 */
angular.module('quay').directive('anchor', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/anchor.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'href': '@href',
      'target': '@target',
      'isOnlyText': '=isOnlyText'
    },
    controller: function($scope, $element) {
    }
  };
  return directiveDefinitionObject;
});