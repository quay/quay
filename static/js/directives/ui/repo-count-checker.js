/**
 * An element which displays a message when the maximum number of private repositories has been
 * reached.
 */
angular.module('quay').directive('repoCountChecker', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-count-checker.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'namespace': '=namespace',
      'planRequired': '=planRequired',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, ApiService, UserService, PlanService, Features) {
      var refresh = function() {
        $scope.planRequired = null;

        if (!$scope.isEnabled || !$scope.namespace || !Features.BILLING) {
          return;
        }

        $scope.checkingPlan = true;
        $scope.isUserNamespace = !UserService.isOrganization($scope.namespace);

        ApiService.getPrivateAllowed($scope.isUserNamespace ? null : $scope.namespace).then(function(resp) {
          $scope.checkingPlan = false;

          if (resp['privateAllowed']) {
            $scope.planRequired = null;
            return;
          }

          if (resp['privateCount'] == null) {
            // Organization where we are not the admin.
            $scope.planRequired = {};
            return;
          }

          // Otherwise, lookup the matching plan.
          PlanService.getMinimumPlan(resp['privateCount'] + 1, !$scope.isUserNamespace, function(minimum) {
            $scope.planRequired = minimum;
          });
        });
      };

      var subscribedToPlan = function(sub) {
        $scope.planChanging = false;
        $scope.subscription = sub;

        PlanService.getPlan(sub.plan, function(subscribedPlan) {
          $scope.subscribedPlan = subscribedPlan;
          refresh();
        });
      };

      $scope.$watch('namespace', refresh);
      $scope.$watch('isEnabled', refresh);

      $scope.upgradePlan = function() {
        var callbacks = {
          'started': function() { $scope.planChanging = true; },
          'opened': function() { $scope.planChanging = true; },
          'closed': function() { $scope.planChanging = false; },
          'success': subscribedToPlan,
          'failure': function(resp) {
            $('#couldnotsubscribeModal').modal();
            $scope.planChanging = false;
          }
        };

        $scope.isUserNamespace = !UserService.isOrganization($scope.namespace);
        var namespace = $scope.isUserNamespace ? null : $scope.namespace;
        PlanService.changePlan($scope, namespace, $scope.planRequired.stripeId, callbacks);
      };
    }
  };
  return directiveDefinitionObject;
});
