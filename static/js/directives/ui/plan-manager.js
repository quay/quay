/**
 * Element for managing subscriptions.
 */
angular.module('quay').directive('planManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/plan-manager.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'user': '=user',
      'organization': '=organization',

      'hasSubscription': '=hasSubscription',

      'readyForPlan': '&readyForPlan',
      'planChanged': '&planChanged'
    },
    controller: function($scope, $element, PlanService, ApiService) {
      $scope.isExistingCustomer = false;

      $scope.parseDate = function(timestamp) {
        return new Date(timestamp * 1000);
      };

      $scope.isPlanVisible = function(plan, subscribedPlan) {
        if ($scope.organization && !PlanService.isOrgCompatible(plan)) {
          return false;
        }

        // A plan is visible if it is not deprecated, or if it is the namespace's current plan.
        if (plan['deprecated']) {
          return subscribedPlan && plan.stripeId === subscribedPlan.stripeId;
        }

        return true;
      };

      $scope.isPlanActive = function(plan, subscribedPlan) {
        if (!subscribedPlan) {
          return false;
        }
        
        return plan.stripeId === subscribedPlan.stripeId;
      };

      $scope.changeSubscription = function(planId, opt_async) {
        if ($scope.planChanging) { return; }

        var callbacks = {
          'opening': function() { $scope.planChanging = true; },
          'started': function() { $scope.planChanging = true; },
          'opened': function() { $scope.planChanging = true; },
          'closed': function() { $scope.planChanging = false; },
          'success': subscribedToPlan,
          'failure': function(resp) {
             $scope.planChanging = false;
          }
        };

        PlanService.changePlan($scope, $scope.organization, planId, callbacks, opt_async);
      };

      $scope.cancelSubscription = function() {
        $scope.changeSubscription(PlanService.getFreePlan());
      };

      var subscribedToPlan = function(sub) {
        $scope.subscription = sub;
        $scope.isExistingCustomer = !!sub['isExistingCustomer'];

        PlanService.getPlanIncludingDeprecated(sub.plan, function(subscribedPlan) {
          $scope.subscribedPlan = subscribedPlan;
          $scope.planUsagePercent = sub.usedPrivateRepos * 100 / $scope.subscribedPlan.privateRepos;

          if ($scope.planChanged) {
            $scope.planChanged({ 'plan': subscribedPlan });
          }

          $scope.planChanging = false;
          $scope.planLoading = false;
          $scope.hasSubscription = subscribedPlan.stripeId != PlanService.getFreePlan();
        });
      };

      var update = function() {
        $scope.planLoading = true;
        if (!$scope.plans) { return; }

        PlanService.getSubscription($scope.organization, subscribedToPlan, function() {
          $scope.isExistingCustomer = false;
          subscribedToPlan({ 'plan': PlanService.getFreePlan() });
        });
      };

      var loadPlans = function() {
        if ($scope.plans || $scope.loadingPlans) { return; }
        if (!$scope.user && !$scope.organization) { return; }

        $scope.loadingPlans = true;
        PlanService.verifyLoaded(function(plans) {
          $scope.plans = plans;
          update();

          if ($scope.readyForPlan) {
            var planRequested = $scope.readyForPlan();
            if (planRequested && planRequested != PlanService.getFreePlan()) {
              $scope.changeSubscription(planRequested, /* async */true);
            }
          }
        });
      };

      // Start the initial download.
      $scope.planLoading = true;
      loadPlans();

      $scope.$watch('organization', loadPlans);
      $scope.$watch('user', loadPlans);
    }
  };
  return directiveDefinitionObject;
});

