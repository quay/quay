(function() {
  /**
   * Page for creating a new organization.
   */
  angular.module('quayPages').config(['pages', function(pages) {
    pages.create('new-organization', 'new-organization.html', NewOrgCtrl, {
      'newLayout': true,
      'title': 'New Organization',
      'description': 'Create a new organization to manage teams and permissions'
    });
  }]);

  function NewOrgCtrl($scope, $routeParams, $timeout, $location, UserService, PlanService, ApiService, CookieService, Features, Config) {
    $scope.Features = Features;
    $scope.Config = Config
    $scope.holder = {};
    $scope.org = {
      'name': $routeParams['namespace'] || ''
    };

    UserService.updateUserIn($scope);

    var requested = $routeParams['plan'];

    if (Features.BILLING) {
      // Load the list of plans.
      PlanService.getPlans(function(plans) {
        $scope.plans = plans;
        $scope.holder.currentPlan = null;
        if (requested) {
          PlanService.getPlan(requested, function(plan) {
            $scope.holder.currentPlan = plan;
          });
        }
      });
    }

    $scope.signedIn = function() {
      if (Features.BILLING) {
        PlanService.handleNotedPlan();
      }
    };

    $scope.signinStarted = function() {
      if (Features.BILLING) {
        PlanService.getMinimumPlan(1, true, function(plan) {
          if (!plan) { return; }
          PlanService.notePlan(plan.stripeId);
        });
      }
    };

    $scope.setPlan = function(plan) {
      $scope.holder.currentPlan = plan;
    };

    $scope.createNewOrg = function() {
      $scope.createError = null;
      $scope.creating = true;

      var org = $scope.org;
      var data = {
        'name': org.name,
        'email': org.email,
        'recaptcha_response': org.recaptcha_response
      };

      ApiService.createOrganization(data).then(function(created) {
        $scope.created = created;

        // Reset the organizations list.
        UserService.load();

        // Set the default namesapce to the organization.
        CookieService.putPermanent('quay.namespace', org.name);

        var showOrg = function() {
          $scope.creating = false;
          $location.path('/organization/' + org.name + '/');
        };

        // If the selected plan is free, simply move to the org page.
        if (!Features.BILLING || $scope.holder.currentPlan.price == 0) {
          showOrg();
          return;
        }

        // Otherwise, show the subscribe for the plan.
        $scope.creating = true;
        var callbacks = {
          'opened': function() { $scope.creating = true; },
          'closed': showOrg,
          'success': showOrg,
          'failure': showOrg
        };

        PlanService.changePlan($scope, org.name, $scope.holder.currentPlan.stripeId, callbacks);
      }, function(resp) {
        $scope.creating = false;
        $scope.createError = ApiService.getErrorMessage(resp);
      });
    };
  }
})();