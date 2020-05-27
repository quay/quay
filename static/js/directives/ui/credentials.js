/**
 * An element which displays a credentials for a build trigger.
 */
angular.module('quay').directive('credentials', function() {
  var directiveDefinitionObject = {
    templateUrl: '/static/directives/credentials.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'trigger': '=trigger'
    },
    controller: function($scope, TriggerService, DocumentationService) {
      $scope.DocumentationService = DocumentationService;
      TriggerService.populateTemplate($scope, 'credentials');
    }
  };
  return directiveDefinitionObject;
});
