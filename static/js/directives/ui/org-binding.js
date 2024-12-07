angular.module('quay').directive('orgBinding', function() {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/org-binding.html',
    restrict: 'C',
    scope: {
      'marketplaceTotal': '=marketplaceTotal',
      'organization': '=organization',
    },
    controller: function($scope, $timeout, PlanService, ApiService) {
      $scope.userMarketplaceSubscriptions = [];
      $scope.orgMarketplaceSubscriptions = [];
      $scope.availableSubscriptions = [];
      $scope.marketplaceLoading = true;
      $scope.bindOrgSuccess = false;
      $scope.removeSkuSuccess = false;

      var groupSubscriptionsBySku = function(subscriptions) {
        const grouped = {};

        subscriptions.forEach(obj => {
          const { sku, ...rest } = obj;
          if(!grouped[sku]) {
            grouped[sku] = [];
          }
          grouped[sku].push(rest);
        });
        return grouped;
      }

      var loadSubscriptions = function() {
        var total = 0;

        if ($scope.organization) {
          PlanService.listOrgMarketplaceSubscriptions($scope.organization, function(marketplaceSubscriptions){
            // group the list of subscriptions by their sku field
            $scope.orgMarketplaceSubscriptions = marketplaceSubscriptions;
            for (var i = 0; i < marketplaceSubscriptions.length; i++) {
              total += (
                marketplaceSubscriptions[i]["quantity"] *
                marketplaceSubscriptions[i]["metadata"]["privateRepos"]
              );
            }
            $scope.marketplaceTotal = total;
          });
        }

        PlanService.listUserMarketplaceSubscriptions(function(marketplaceSubscriptions){
          if(!marketplaceSubscriptions) {
            $scope.marketplaceLoading = false;
            return;
          }
          let notBound = [];
          $scope.userMarketplaceSubscriptions = marketplaceSubscriptions;

          for (var i = 0; i < marketplaceSubscriptions.length; i++) {
            if (marketplaceSubscriptions[i]["assigned_to_org"] === null) {
              if(!($scope.organization)){
                total += (
                  marketplaceSubscriptions[i]["quantity"] *
                  marketplaceSubscriptions[i]["metadata"]["privateRepos"]
                );
              }
              notBound.push(marketplaceSubscriptions[i]);
            }
          }
          if(!($scope.organization)){
            $scope.marketplaceTotal = total;
          }
          $scope.availableSubscriptions = notBound;
          $scope.marketplaceLoading = false;
        });
      }

      var update = function() {
        $scope.marketplaceLoading = true;
        loadSubscriptions();
      }

      $scope.bindSku = function(subscriptionToBind, bindingQuantity) {
        let subscription;
        try {
          // Try to parse if it's a JSON string
          subscription = typeof subscriptionToBind === 'string' ? JSON.parse(subscriptionToBind) : subscriptionToBind;
        } catch (e) {
          // If parsing fails, assume it's already an object
          subscription = subscriptionToBind;
        }
        $scope.marketplaceLoading = true;
        const requestData = {};
        requestData["subscriptions"] = [];
        const subscriptionData = {
          "subscription_id": subscription["id"]
        };
        if (bindingQuantity !== undefined) {
          subscriptionData["quantity"] = bindingQuantity;
        }
        requestData["subscriptions"].push(subscriptionData);
        PlanService.bindSkuToOrg(requestData, $scope.organization, function(resp){
          if (resp === "Okay"){
            bindSkuSuccessMessage();
          }
          else {
            displayError(resp.message);
          }
        });
      };

      $scope.batchRemoveSku = function(subscriptionToRemove) {
        let subscription = JSON.parse(subscriptionToRemove);
        const requestData = {};
        requestData["subscriptions"] = [];
        requestData["subscriptions"].push({"subscription_id": subscription["subscription_id"]});
        PlanService.batchRemoveSku(requestData, $scope.organization, function(resp){
          if (resp == "") {
            removeSkuSuccessMessage();
          }
          else {
            displayError(resp.message);
          }
        });
      };

      var displayError = function (message = "Could not update org") {
        let errorDisplay = ApiService.errorDisplay(message, () => {
        });
        return errorDisplay;
      }

      var bindSkuSuccessMessage = function () {
        $timeout(function () {
          $scope.bindOrgSuccess = true;
        }, 1);
        $timeout(function () {
          $scope.bindOrgSuccess = false;
        }, 5000)
      };

      var removeSkuSuccessMessage = function () {
        $timeout(function () {
          $scope.removeSkuSuccess = true;
        }, 1);
        $timeout(function () {
          $scope.removeSkuSuccess = false;
        }, 5000)
      };

      loadSubscriptions();

      $scope.$watch('bindOrgSuccess', function(){
        if($scope.bindOrgSuccess === true) { update(); }
      });
      $scope.$watch('removeSkuSuccess', function(){
        if($scope.removeSkuSuccess === true) { update(); }
      });

    }
  };
  return directiveDefinitionObject;
});
