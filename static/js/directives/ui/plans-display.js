/**
 * An element which displays the plans page content. Put into a directive for encapsulating the tab
 * changing code.
 */
angular.module('quay').directive('plansDisplay', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/plans-display.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
    },
    controller: function($scope, $element, $routeParams, $timeout, UserService, PlanService, UIService) {
      // Monitor any user changes and place the current user into the scope.
      UserService.updateUserIn($scope);

      // Watch for tab changes.
      UIService.initializeTabs($scope, $element);

      $scope.signedIn = function() {
        $('#signinModal').modal('hide');
        PlanService.handleNotedPlan();
      };

      $scope.qeStartTrial = function() {
        $('#redhatManagerDialog').modal('show');
      };

      $scope.buyNow = function(plan) {
        PlanService.notePlan(plan);
        if ($scope.user && !$scope.user.anonymous) {
          PlanService.handleNotedPlan();
        } else {
          $timeout(function() {
            $('#signinModal').modal({});
          }, 0);
        }
      };

      // Load the list of plans.
      PlanService.getPlans(function(plans) {
        $scope.plans = plans;

        for (var i = 0; i < $scope.plans.length; ++i) {
          var plan = plans[i];
          if (plan.privateRepos > 20 && !plan.plans_page_hidden) {
            $scope.dropdownPlan = plan.stripeId;
            break
          }
        }

        if ($scope && $routeParams['trial-plan']) {
          $scope.buyNow($routeParams['trial-plan']);
        }
      }, /* include the personal plan */ true);
    }
  };
  return directiveDefinitionObject;
});
