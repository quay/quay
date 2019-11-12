/**
 * Helper service for loading, changing and working with subscription plans.
 */
angular.module('quay')
       .factory('PlanService', ['KeyService', 'UserService', 'CookieService', 'ApiService', 'Features', 'Config', '$location',

function(KeyService, UserService, CookieService, ApiService, Features, Config, $location) {
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
          $location.path('/user').search('plan', planId);
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

  planService.setSubscription = function(orgname, planId, success, failure, opt_token) {
    if (!Features.BILLING) { return; }

    var subscriptionDetails = {
      plan: planId
    };

    if (opt_token) {
      subscriptionDetails['token'] = opt_token.id;
    }

    ApiService.updateSubscription(orgname, subscriptionDetails).then(function(resp) {
      success(resp);
      planService.getPlan(planId, function(plan) {
        for (var i = 0; i < listeners.length; ++i) {
          listeners[i]['callback'](plan);
        }
      });
    }, failure);
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
          var title = cardInfo.last4 ? 'Subscribe' : 'Start Trial ({{amount}} plan)';
          planService.showSubscribeDialog($scope, orgname, planId, callbacks, title, /* async */true);
          return;
        }

        previousSubscribeFailure = false;

        planService.setSubscription(orgname, planId, callbacks['success'], function(resp) {
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

    var submitted = false;
    var submitToken = function(token) {
      if (submitted) { return; }
      submitted = true;
      $scope.$apply(function() {
        if (callbacks['started']) {
          callbacks['started']();
        }

        var cardInfo = {
          'token': token.id
        };

        ApiService.setCard(orgname, cardInfo).then(callbacks['success'], function(resp) {
          planService.handleCardError(resp);
          callbacks['failure'](resp);
        });
      });
    };

    var email = planService.getEmail(orgname);
    StripeCheckout.open({
        key:            KeyService.stripePublishableKey,
        email:          email,
        currency:       'usd',
        name:           'Update credit card',
        description:    'Enter your credit card number',
        panelLabel:     'Update',
        token:          submitToken,
        image:          'static/img/quay-icon-stripe.png',
        billingAddress: true,
        zipCode:        true,
        opened:         function() { $scope.$apply(function() { callbacks['opened']() }); },
        closed:         function() { $scope.$apply(function() { callbacks['closed']() }); }
     });
  };

  planService.getEmail = function(orgname) {
    var email = null;
    if (UserService.currentUser()) {
      email = UserService.currentUser().email;

      if (orgname) {
        org = UserService.getOrganization(orgname);
        if (org) {
          emaiil = org.email;
        }
      }
    }
    return email;
  };

  planService.showSubscribeDialog = function($scope, orgname, planId, callbacks, opt_title, opt_async) {
    if (!Features.BILLING) { return; }

    // If the async parameter is true and this is a browser that does not allow async popup of the
    // Stripe dialog (such as Mobile Safari or IE), show a bootbox to show the dialog instead.
    var isIE = navigator.appName.indexOf("Internet Explorer") != -1;
    var isMobileSafari = navigator.userAgent.match(/(iPod|iPhone|iPad)/) && navigator.userAgent.match(/AppleWebKit/);

    if (opt_async && (isIE || isMobileSafari)) {
      bootbox.dialog({
        "message": "Please click 'Subscribe' to continue",
        "buttons": {
          "subscribe": {
            "label": "Subscribe",
            "className": "btn-primary",
            "callback": function() {
              planService.showSubscribeDialog($scope, orgname, planId, callbacks, opt_title, false);
            }
          },
          "close": {
            "label": "Cancel",
            "className": "btn-default"
          }
        }
      });
      return;
    }

    if (callbacks['opening']) {
      callbacks['opening']();
    }

    var submitted = false;
    var submitToken = function(token) {
      if (submitted) { return; }
      submitted = true;

      if (Config.MIXPANEL_KEY) {
        mixpanel.track('plan_subscribe');
      }

      $scope.$apply(function() {
        if (callbacks['started']) {
          callbacks['started']();
        }
        planService.setSubscription(orgname, planId, callbacks['success'], callbacks['failure'], token);
      });
    };

    planService.getPlan(planId, function(planDetails) {
      var email = planService.getEmail(orgname);
      StripeCheckout.open({
        key:            KeyService.stripePublishableKey,
        email:          email,
        amount:         planDetails.price,
        currency:       'usd',
        name:           'Quay ' + planDetails.title + ' Subscription',
        description:    'Up to ' + planDetails.privateRepos + ' private repositories',
        panelLabel:     opt_title || 'Subscribe',
        token:          submitToken,
        image:          'static/img/quay-icon-stripe.png',
        billingAddress: true,
        zipCode:        true,
        opened:         function() { $scope.$apply(function() { callbacks['opened']() }); },
        closed:         function() { $scope.$apply(function() { callbacks['closed']() }); }
      });
    });
  };

  return planService;
}]);