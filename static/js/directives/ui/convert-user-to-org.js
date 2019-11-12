/**
 * Displays a panel for converting the current user to an organization.
 */
angular.module('quay').directive('convertUserToOrg', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/convert-user-to-org.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'info': '=info'
    },
    controller: function($scope, $element, $location, Features, PlanService, Config, ApiService, CookieService, UserService) {
      $scope.convertStep = 0;
      $scope.org = {};
      $scope.loading = false;
      $scope.user = null;
      $scope.Features = Features;

      $scope.$watch('info', function(info) {
        if (info && info.user) {
          $scope.user = info.user;
          $scope.accountType = 'user';
          $scope.convertStep = 0;
          $('#convertAccountModal').modal({});
        }
      });

      $scope.showConvertForm = function() {
        $scope.convertStep = 1;
      };

      $scope.nextStep = function() {
        if (Features.BILLING) {
          PlanService.getMatchingBusinessPlan(function(plan) {
            $scope.org.plan = plan;
          });

          PlanService.getPlans(function(plans) {
            $scope.orgPlans = plans;
          });

           $scope.convertStep = 2;
        } else {
          $scope.performConversion();
        }
      };

      $scope.performConversion = function() {
        if (Config.AUTHENTICATION_TYPE != 'Database') { return; }
        $scope.convertStep = 3;

        var errorHandler = ApiService.errorDisplay(function() {
          $('#convertAccountModal').modal('hide');
        });

        var data = {
          'adminUser': $scope.org.adminUser,
          'adminPassword': $scope.org.adminPassword,
          'plan': $scope.org.plan ? $scope.org.plan.stripeId : ''
        };

        ApiService.convertUserToOrganization(data).then(function(resp) {
          CookieService.putPermanent('quay.namespace', $scope.user.username);
          UserService.load();
          $('#convertAccountModal').modal('hide');
          $location.path('/');
        }, errorHandler);
      };
    }
  };
  return directiveDefinitionObject;
});