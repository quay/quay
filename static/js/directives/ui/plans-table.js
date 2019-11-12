/**
 * An element which shows a table of all the defined subscription plans and allows one to be
 * highlighted.
 */
angular.module('quay').directive('plansTable', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/plans-table.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'plans': '=plans',
      'currentPlan': '=currentPlan'
    },
    controller: function($scope, $element) {
      $scope.setPlan = function(plan) {
        $scope.currentPlan = plan;
      };
    }
  };
  return directiveDefinitionObject;
});