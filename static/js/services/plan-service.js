/**
 * Helper service for loading, changing and working with subscription plans.
 */
angular.module('quay')
  .factory('PlanService', ['KeyService', 'UserService', 'CookieService', 'ApiService', 'Features', 'Config', '$location', '$timeout',
function(KeyService, UserService, CookieService, ApiService, Features, Config, $location, $timeout) {
  var plans = null;
  var planDict = {};
  var planService = {};
  var listeners = [];

  var previousSubscribeFailure = false;

  planService.getFreePlan = function() {
    return 'free';
  };

  planService.registerListener = function(obj, callback) {
    listeners.push({'obj': obj, 'callback': callback});
  };

  planService.unregisterListener = function(obj) {
    for (var i = 0; i < listeners.length; ++i) {
      if (listeners[i].obj == obj) {
        listeners.splice(i, 1);
        break;
      }
    }
  };

  planService.notePlan = function(planId) {
    if (Features.BILLING) {
      CookieService.putSession('quay.notedplan', planId);
    }
  };

  planService.isOrgCompatible = function(plan) {
    return plan['stripeId'] == planService.getFreePlan() || plan['bus_features'];
  };

  planService.getMatchingBusinessPlan = function(callback) {
    planService.getPlans(function() {
      planService.getSubscription(null, function(sub) {
        var plan = planDict[sub.plan];
        if (!plan) {
          planService.getMinimumPlan(0, true, callback);
          return;
        }

        var count = Math.max(sub.usedPrivateRepos, plan.privateRepos);
        planService.getMinimumPlan(count, true, callback);
      }, function() {
        planService.getMinimumPlan(0, true, callback);
      });
    });
  };

  planService.handleNotedPlan = function() {
    var planId = planService.getAndResetNotedPlan();
    if (!planId || !Features.BILLING) { return false; }

    UserService.load(function() {
      if (UserService.currentUser().anonymous) {
        return;
      }

      planService.getPlan(planId, function(plan) {
        if (planService.isOrgCompatible(plan)) {
          $location.path('/organizations/new').search('plan', planId);
        } else {
          const username = UserService.currentUser().username;
          $location.path(`/user/${username}/billing`);
        }
      });
    });

    return true;
  };

  planService.getAndResetNotedPlan = function() {
    var planId = CookieService.get('quay.notedplan');
    CookieService.clear('quay.notedplan');
    return planId;
  };

  planService.handleCardError = function(resp) {
    if (!planService.isCardError(resp)) { return; }

    bootbox.dialog({
      "message": resp.data.carderror,
      "title": "Credit card issue",
      "buttons": {
        "close": {
          "label": "Close",
          "className": "btn-primary"
        }
      }
    });
  };

  planService.isCardError = function(resp) {
    return resp && resp.data && resp.data.carderror;
  };

  planService.verifyLoaded = function(callback) {
    if (!Features.BILLING) { return; }

    if (plans && plans.length) {
      callback(plans);
      return;
    }

    ApiService.listPlans().then(function(data) {
      plans = data.plans || [];
      for(var i = 0; i < plans.length; i++) {
        planDict[plans[i].stripeId] = plans[i];
      }
      callback(plans);
    }, function() { callback([]); });
  };

  planService.getPlans = function(callback, opt_includePersonal) {
    planService.verifyLoaded(function(plans) {
      var filtered = [];
      for (var i = 0; i < plans.length; ++i) {
        var plan = plans[i];
        if (plan['deprecated']) { continue; }
        if (!opt_includePersonal && !planService.isOrgCompatible(plan)) { continue; }
        filtered.push(plan);
      }
      callback(filtered);
    });
  };

  planService.getPlan = function(planId, callback) {
    planService.getPlanIncludingDeprecated(planId, function(plan) {
      if (!plan['deprecated']) {
        callback(plan);
      }
    });
  };

  planService.getPlanIncludingDeprecated = function(planId, callback) {
    planService.verifyLoaded(function() {
      if (planDict[planId]) {
        callback(planDict[planId]);
      }
    });
  };

  planService.getPlanImmediately = function(planId) {
    // Get the plan by name, without bothering to check if the plans are loaded.
    // This method will return undefined if planId is undefined or null, or if
    // the planDict has not yet been loaded.
    return planDict[planId];
  };

  planService.getMinimumPlan = function(privateCount, isBusiness, callback) {
    planService.getPlans(function(plans) {
      for (var i = 0; i < plans.length; i++) {
        var plan = plans[i];
        if (plan.privateRepos >= privateCount) {
          callback(plan);
          return;
        }
      }

      callback(null);
    }, /* include personal */!isBusiness);
  };

  planService.getSubscription = function(orgname, success, failure) {
    if (!Features.BILLING) { return; }

    ApiService.getSubscription(orgname).then(success, failure);
  };

  planService.createSubscription = function($scope, orgname, planId, success, failure) {
    if (!Features.BILLING) { return; }

    var redirectURL = $scope.redirectUrl || window.location.toString();
    var subscriptionDetails = {
      plan: planId,
      success_url: redirectURL,
      cancel_url: redirectURL
    };

    ApiService.createSubscription(orgname, subscriptionDetails).then(
      function(resp) {
        $timeout(function() {
          success(resp);
          document.location = resp.url;
        }, 250);
      },
      failure
    );
  };

  planService.updateSubscription = function($scope, orgname, planId, success, failure) {
    if (!Features.BILLING) { return; }
    
    var subscriptionDetails = {
      plan: planId,
    };
    
    planService.getPlan(planId, function(plan) {
      ApiService.updateSubscription(orgname, subscriptionDetails).then(
	function(resp) {
	  success(resp);
	  for (var i = 0; i < listeners.length; ++i) {
            listeners[i]['callback'](plan);
	  }
	},
	failure
      );
    });
  };  

  planService.getCardInfo = function(orgname, callback) {
    if (!Features.BILLING) { return; }

    ApiService.getCard(orgname).then(function(resp) {
      callback(resp.card);
    }, function() {
      callback({'is_valid': false});
    });
  };

  planService.changePlan = function($scope, orgname, planId, callbacks, opt_async) {
    if (!Features.BILLING) { return; }

    if (callbacks['started']) {
      callbacks['started']();
    }

    planService.getSubscription(orgname, function(sub) {
      planService.getPlanIncludingDeprecated(sub.plan, function(subscribedPlan) {
        planService.changePlanInternal($scope, orgname, planId, callbacks, opt_async,
                                       subscribedPlan.price > 0);
      });
    }, function() {
      planService.changePlanInternal($scope, orgname, planId, callbacks, opt_async, false);
    });
  };

  planService.changePlanInternal = function($scope, orgname, planId, callbacks, opt_async,
                                            opt_reuseCard) {
    if (!Features.BILLING) { return; }

    planService.getPlan(planId, function(plan) {
      if (orgname && !planService.isOrgCompatible(plan)) { return; }

      planService.getCardInfo(orgname, function(cardInfo) {

        if (plan.price > 0 && (previousSubscribeFailure || !cardInfo.last4 || !opt_reuseCard)) {
          var redirectURL = $scope.redirectUrl || window.location.toString();
          var setCardDetails = {
            success_url: redirectURL,
            cancel_url: redirectURL
          };

          planService.createSubscription($scope, orgname, planId, callbacks['success'], function(resp) {
            previousSubscribeFailure = true;
            planService.handleCardError(resp);
            callbacks['failure'](resp);
          });
          return;
        }

        previousSubscribeFailure = false;

        planService.updateSubscription($scope, orgname, planId, callbacks['success'], function(resp) {
	  previousSubscribeFailure = true;
	  planService.handleCardError(resp);
	  callbacks['failure'](resp);
	});
      });
    });
  };

  planService.changeCreditCard = function($scope, orgname, callbacks) {
    if (!Features.BILLING) { return; }

    if (callbacks['opening']) {
      callbacks['opening']();
    }

    var redirectURL = $scope.redirectUrl || window.location.toString();
    var setCardDetails = {
      success_url: redirectURL,
      cancel_url: redirectURL
    };

    ApiService.setCard(orgname, setCardDetails).then(
      function(resp) {
        $timeout(function() {
          callbacks['success'](resp)
          document.location = resp.url;
        }, 250);
        
      },
      function(resp) {
        planService.handleCardError(resp);
        callbacks['failure'](resp);
      }
    );
  };

  return planService;
}]);
