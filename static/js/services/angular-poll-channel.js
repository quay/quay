/**
 * Specialized class for conducting an HTTP poll, while properly preventing multiple calls.
 */
angular.module('quay').factory('AngularPollChannel',
    ['ApiService', '$timeout', 'DocumentVisibilityService', 'CORE_EVENT', '$rootScope',
    function(ApiService, $timeout, DocumentVisibilityService, CORE_EVENT, $rootScope) {
  var _PollChannel = function(scope, requester, opt_sleeptime) {
    this.scope_ = scope;
    this.requester_ = requester;
    this.sleeptime_ = opt_sleeptime || (60 * 1000 /* 60s */);
    this.timer_ = null;

    this.working = false;
    this.polling = false;
    this.skipping = false;

    var that = this;

    var visibilityHandler = $rootScope.$on(CORE_EVENT.DOC_VISIBILITY_CHANGE, function() {
      // If the poll channel was skipping because the visibility was hidden, call it immediately.
      if (that.skipping && !DocumentVisibilityService.isHidden()) {
        that.call_();
      }
    });

    scope.$on('$destroy', function() {
      that.stop();
      visibilityHandler();
    });
  };

  _PollChannel.prototype.setSleepTime = function(sleepTime) {
    this.sleeptime_ = sleepTime;
    this.stop();
    this.start(true);
  };

  _PollChannel.prototype.stop = function() {
    if (this.timer_) {
      $timeout.cancel(this.timer_);
      this.timer_ = null;
      this.polling = false;
    }

    this.skipping = false;
    this.working = false;
  };

  _PollChannel.prototype.start = function(opt_skipFirstCall) {
    // Make sure we invoke call outside the normal digest cycle, since
    // we'll call $scope.$apply ourselves.
    var that = this;
    setTimeout(function() {
      if (opt_skipFirstCall) {
        that.setupTimer_();
        return;
      }

      that.call_();
    }, 0);
  };

  _PollChannel.prototype.call_ = function() {
    if (this.working) { return; }

    // If the document is currently hidden, skip the call.
    if (DocumentVisibilityService.isHidden()) {
      this.skipping = true;
      this.setupTimer_();
      return;
    }

    var that = this;
    this.working = true;

    $timeout(function() {
      that.requester_(function(status) {
        if (status) {
          that.working = false;
          that.skipping = false;
          that.setupTimer_();
        } else {
          that.stop();
        }
      });
    }, 0);
  };

  _PollChannel.prototype.setupTimer_ = function() {
    if (this.timer_) { return; }

    var that = this;
    this.polling = true;
    this.timer_ = $timeout(function() {
      that.timer_ = null;
      that.call_();
    }, this.sleeptime_)
  };

  var service = {
    'create': function(scope, requester, opt_sleeptime) {
      return new _PollChannel(scope, requester, opt_sleeptime);
    }
  };

  return service;
}]);
