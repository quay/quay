/**
 * An element which displays the billing options for a user or an organization.
 */
angular.module('quay').directive('billingManagementPanel', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/billing-management-panel.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'user': '=user',
      'organization': '=organization',
      'isEnabled': '=isEnabled',
      'subscriptionStatus': '=subscriptionStatus'
    },
    controller: function($scope, $element, PlanService, ApiService, Features) {
      $scope.currentCard = null;
      $scope.subscription = null;
      $scope.updating = true;
      $scope.changeReceiptsInfo = null;
      $scope.context = {};
      $scope.subscriptionStatus = 'loading';

      var setSubscription = function(sub) {
        $scope.subscription = sub;

        // Load the plan info.
        PlanService.getPlanIncludingDeprecated(sub['plan'], function(plan) {
          $scope.currentPlan = plan;

          if (!sub.hasSubscription) {
            $scope.updating = false;
            $scope.subscriptionStatus = 'none';
            return;
          }

          // Load credit card information.
          PlanService.getCardInfo($scope.organization ? $scope.organization.name : null, function(card) {
            $scope.currentCard = card;
            $scope.subscriptionStatus = 'valid';
            $scope.updating = false;
          });
        });
      };

      var update = function() {
        if (!$scope.isEnabled || !($scope.user || $scope.organization) || !Features.BILLING) {
          return;
        }

        $scope.entity = $scope.user ? $scope.user : $scope.organization;
        $scope.invoice_email = $scope.entity.invoice_email;
        $scope.invoice_email_address = $scope.entity.invoice_email_address || $scope.entity.email;

        $scope.updating = true;

        // Load plan information.
        PlanService.getSubscription($scope.organization, setSubscription, function() {
          setSubscription({ 'plan': PlanService.getFreePlan() });
        });
      };

      // Listen to plan changes.
      PlanService.registerListener(this, function(plan) {
        if (plan && plan.price > 0) {
          update();
        }
      });

      $scope.$on('$destroy', function() {
        PlanService.unregisterListener(this);
      });

      $scope.$watch('isEnabled', update);
      $scope.$watch('organization', update);
      $scope.$watch('user', update);

      $scope.getEntityPrefix = function() {
        if ($scope.organization) {
          return '/organization/' + $scope.organization.name;
        } else {
          return '/user/' + $scope.user.username;
        }
      };

      $scope.changeCreditCard = function() {
        var callbacks = {
          'opened': function() {  },
          'closed': function() {  },
          'started': function() {  },
          'success': function(resp) {
             $scope.currentCard = resp.card;
             update();
          },
          'failure': function(resp) {
             if (!PlanService.isCardError(resp)) {
               bootbox.alert('Could not change credit card. Please try again later.');
             }
          }
        };

        PlanService.changeCreditCard($scope, $scope.organization ? $scope.organization.name : null, callbacks);
      };

      $scope.getCreditImage = function(creditInfo) {
        if (!creditInfo || !creditInfo.type) { return 'credit.png'; }

        var kind = creditInfo.type.toLowerCase() || 'credit';
        var supported = {
          'american express': 'amex',
          'credit': 'credit',
          'diners club': 'diners',
          'discover': 'discover',
          'jcb': 'jcb',
          'mastercard': 'mastercard',
          'visa': 'visa'
        };

        kind = supported[kind] || 'credit';
        return kind + '.png';
      };

      $scope.changeReceipts = function(info, callback) {
        $scope.entity['invoice_email'] = info['sendOption'] || false;
        $scope.entity['invoice_email_address'] = info['address'] || $scope.entity.email;

        var errorHandler = ApiService.errorDisplay('Could not change billing options', callback);
        ApiService.changeDetails($scope.organization, $scope.entity).then(function(resp) {
          callback(true);
          update();
        }, errorHandler);
      };

      $scope.showChangeReceipts = function() {
        $scope.changeReceiptsInfo = {
          'sendOption': $scope.invoice_email,
          'address': $scope.invoice_email_address
        };
      };
    }
  };
  return directiveDefinitionObject;
});