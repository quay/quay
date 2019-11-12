/**
 * An element which shows information about a registered OAuth application.
 */
angular.module('quay').directive('applicationInfo', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/application-info.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'application': '=application'
    },
    controller: function($scope, $element, ApiService) {}
  };
  return directiveDefinitionObject;
});

