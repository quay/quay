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
      $scope.userMarketplaceSubscriptions = {};
      $scope.orgMarketplaceSubscriptions = {};
      $scope.availableSubscriptions = {};
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
            // $scope.orgMarketplaceSubscriptions = marketplaceSubscriptions
            // group the list of subscriptions by their sku field
            $scope.orgMarketplaceSubscriptions = groupSubscriptionsBySku(marketplaceSubscriptions);
            for (var i = 0; i < marketplaceSubscriptions.length; i++) {
              total += marketplaceSubscriptions[i]["metadata"]["privateRepos"];
            }
            $scope.marketplaceTotal = total;
          });
        }

        PlanService.listUserMarketplaceSubscriptions(function(marketplaceSubscriptions){
          let notBound = [];
          $scope.userMarketplaceSubscriptions = groupSubscriptionsBySku(marketplaceSubscriptions);

          for (var i = 0; i < marketplaceSubscriptions.length; i++) {
            if (marketplaceSubscriptions[i]["assigned_to_org"] === null) {
              if(!($scope.organization)){
                total += marketplaceSubscriptions[i]["metadata"]["privateRepos"];
              }
              notBound.push(marketplaceSubscriptions[i]);
            }
          }
          if(!($scope.organization)){
            $scope.marketplaceTotal = total;
          }
          $scope.availableSubscriptions = groupSubscriptionsBySku(notBound);
          $scope.marketplaceLoading = false;
        });
      }

      var update = function() {
        $scope.marketplaceLoading = true;
        loadSubscriptions();
      }

      $scope.bindSku = function(subscriptions, numSubscriptions) {
        let subscriptionArr = JSON.parse(subscriptions);
        // if(numSubscriptions > subscriptionArr.length){
        //   displayError("number of subscriptions exceeds total amount");
        //   return;
        // }
        $scope.marketplaceLoading = true;
        const requestData = {};
        requestData["subscriptions"] = [];
        for(var i = 0; i < numSubscriptions; ++i) {
          var subscriptionObject = {};
          var subscriptionId = subscriptionArr[i].id;
          subscriptionObject.subscription_id = subscriptionId;
          requestData["subscriptions"].push(subscriptionObject);
        }
        PlanService.bindSkuToOrg(requestData, $scope.organization, function(resp){
          if (resp === "Okay"){
            bindSkuSuccessMessage();
          }
          else {
            displayError(resp.message);
          }
        });
      };

      $scope.batchRemoveSku = function(removals, numRemovals) {
        let removalArr = JSON.parse(removals);
        const requestData = {};
        requestData["subscriptions"] = [];
        for(var i = 0; i < numRemovals; ++i){
          var subscriptionObject = {};
          var subscriptionId = removalArr[i].subscription_id;
          subscriptionObject.subscription_id = subscriptionId;
          requestData["subscriptions"].push(subscriptionObject);
        }
        PlanService.batchRemoveSku(requestData, $scope.organization, function(resp){
          if (resp === "Deleted") {
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
