/**
 * Service which provides helper methods for performing some simple UI operations.
 */
angular.module('quay').factory('UIService', ['$timeout', '$rootScope', '$location', 'ApiService', function($timeout, $rootScope, $location, ApiService) {
  var CheckStateController = function(items, itemKey) {
    this.items = items;
    this.checked = [];

    this.allItems_ = items;
    this.allCheckedMap_ = {};

    this.itemKey_ = itemKey;
    this.listeners_ = [];
    this.page_ = null;
    this.lastChanged_ = null;

    this.ApiService = ApiService
  };

  CheckStateController.prototype.listen = function(callback) {
    this.listeners_.push(callback);
  };

  CheckStateController.prototype.isChecked = function(item) {
    return !!this.allCheckedMap_[item[this.itemKey_]];
  };

  CheckStateController.prototype.toggleItem = function(item, opt_shift) {
    if (opt_shift && this.lastChanged_) {
      var itemIndex = $.inArray(item, this.items);
      var lastIndex = $.inArray(this.lastChanged_, this.items);

      if (itemIndex >= 0 && lastIndex >= 0) {
        var startIndex = Math.min(itemIndex, lastIndex);
        var endIndex = Math.max(itemIndex, lastIndex);
        var shouldCheck = this.isChecked(this.lastChanged_);

        for (var i = startIndex; i <= endIndex; ++i) {
          if (shouldCheck) {
            this.checkItem(this.items[i]);
          } else {
            this.uncheckItem(this.items[i]);
          }
        }

        return;
      }
    }

    if (this.isChecked(item)) {
      this.uncheckItem(item);
    } else {
      this.checkItem(item);
    }
  };

  CheckStateController.prototype.toggleItems = function(opt_filter) {
    this.lastChanged_= null;
    this.updateMap_(this.checked, false);

    if (this.checked.length) {
      this.checked = [];
    } else {
      if (opt_filter) {
        this.checked = this.items.filter((item) => (opt_filter.indexOf(item) >= 0));
      } else {
        this.checked = this.items.slice();
      }
    }

    this.updateMap_(this.checked, true);
    this.callListeners_();
  };

  CheckStateController.prototype.setPage = function(page, pageSize) {
    this.items = this.allItems_.slice(page * pageSize, (page + 1) * pageSize);
    this.rebuildCheckedList_();
  };

  CheckStateController.prototype.setChecked = function(items) {
    this.allCheckedMap_ = {};
    this.updateMap_(items, true);
    this.rebuildCheckedList_();
  };

  CheckStateController.prototype.rebuildCheckedList_ = function() {
    var that = this;
    this.checked = [];
    this.allItems_.forEach(function(item) {
      if (that.allCheckedMap_[item[that.itemKey_]]) {
        that.checked.push(item);
      }
    });

    this.callListeners_();
  };

  CheckStateController.prototype.updateMap_ = function(items, is_checked) {
    var that = this;
    items.forEach(function(item) {
      if (item == null) { return; }
      that.allCheckedMap_[item[that.itemKey_]] = is_checked;
    });
  };

  CheckStateController.prototype.checkByFilter = function(filter, opt_secondaryFilter) {
    this.updateMap_(this.checked, false);
    
    var filterFunc = filter;
    if (opt_secondaryFilter) {
      filterFunc = (item) => (opt_secondaryFilter.indexOf(item) >= 0 && filter(item));
    }

    this.checked = $.grep(this.items, filterFunc);

    this.updateMap_(this.checked, true);
    this.callListeners_();
  };

  CheckStateController.prototype.checkItem = function(item) {
    if (this.isChecked(item)) {
      return;
    }

    this.lastChanged_ = item;
    this.checked.push(item);
    this.allCheckedMap_[item[this.itemKey_]] = true;
    this.callListeners_();
  };

  CheckStateController.prototype.uncheckItem = function(item) {
    if (!this.isChecked(item)) {
      return;
    }

    this.lastChanged_ = item;
    this.checked = $.grep(this.checked, function(cItem) {
      return cItem != item;
    });

    this.allCheckedMap_[item[this.itemKey_]] = false;
    this.callListeners_();
  };

  CheckStateController.prototype.callListeners_ = function() {
    var that = this;
    var allCheckedMap = this.allCheckedMap_;
    var allChecked = [];

    this.allItems_.forEach(function(item) {
      var key = item[that.itemKey_];
      if (!!allCheckedMap[key]) {
        allChecked.push(item);
      }
    });

    this.listeners_.map(function(listener) {
      listener(allChecked, that.checked);
    });
  };

  //////////////////////////////////////////////////////////////////////////////////////

  var uiService = {};

  uiService.hidePopover = function(elem) {
    var popover = $(elem).data('bs.popover');
    if (popover) {
      popover.hide();
    }
  };

  uiService.showPopover = function(elem, content, opt_placement) {
    var popover = $(elem).data('bs.popover');
    if (!popover) {
      $(elem).popover({'content': '-', 'placement': opt_placement || 'left'});
    }

    setTimeout(function() {
      var popover = $(elem).data('bs.popover');
      popover.options.content = content;
      popover.show();
    }, 500);
  };

  uiService.showFormError = function(elem, result, opt_placement) {
    var message =  ApiService.getErrorMessage(result, 'error');
    if (message) {
      uiService.showPopover(elem, message, opt_placement || 'bottom');
    } else {
      uiService.hidePopover(elem);
    }
  };

  uiService.createCheckStateController = function(items, opt_checked) {
    return new CheckStateController(items, opt_checked);
  };

  uiService.showPasswordDialog = function(message, callback, opt_canceledCallback) {
    var success = function() {
      var password = $('#passDialogBox').val();
      $('#passDialogBox').val('');
      callback(password);
    };

    var canceled = function() {
      $('#passDialogBox').val('');
      opt_canceledCallback && opt_canceledCallback();
    };

    var box = bootbox.dialog({
      "message": message +
        '<form style="margin-top: 10px" action="javascript:$(\'.btn-continue\').click();void(0)">' +
        '<input id="passDialogBox" class="form-control" type="password" placeholder="Current Password">' +
        '</form>',
      "title": 'Please Verify',
      "buttons": {
        "verify": {
          "label": "Verify",
          "className": "btn-success btn-continue",
          "callback": success
        },
        "close": {
          "label": "Cancel",
          "className": "btn-default",
          "callback": canceled
        }
      }
    });

    box.bind('shown.bs.modal', function(){
      box.find("input").focus();
      box.find("form").submit(function() {
        if (!$('#passDialogBox').val()) { return; }
        box.modal('hide');
        success();
      });
    });
  };

  uiService.clickElement = function(el) {
    // From: http://stackoverflow.com/questions/16802795/click-not-working-in-mocha-phantomjs-on-certain-elements
    var ev = document.createEvent("MouseEvent");
    ev.initMouseEvent(
      "click",
       true /* bubble */, true /* cancelable */,
       window, null,
       0, 0, 0, 0, /* coordinates */
       false, false, false, false, /* modifier keys */
       0 /*left*/, null);
    el.dispatchEvent(ev);
  };

  uiService.initializeTabs = function(scope, element, opt_clickCallback, opt_rememberCookie) {
    var locationListener = null;
    var disposed = false;

    var changeTab = function(activeTab) {
      if (disposed) { return; }

      $('a[data-toggle="tab"]').each(function(index) {
        var tabName = this.getAttribute('data-target').substr(1);
        if (tabName != activeTab) {
          return;
        }

        if ($(this).parent().hasClass('active')) {
          return;
        }

        if (this.clientWidth == 0) {
          setTimeout(function() {
            changeTab(activeTab);
          }, 100);
          return;
        }

        var elem = this;
        setTimeout(function() {
          uiService.clickElement(elem);
        }, 0);
      });
    };

    var resetDefaultTab = function() {
      if (disposed) { return; }

      $timeout(function() {
        element.find('a[data-toggle="tab"]').each(function(index) {
          if (index == 0) {
            var elem = this;
            setTimeout(function() {
              uiService.clickElement(elem);
            }, 0);
          }
        });
      });
    };

    var checkTabs = function() {
      if (disposed) { return; }

      // Poll until we find the tabs.
      var tabs = element.find('a[data-toggle="tab"]');
      if (tabs.length == 0) {
        $timeout(checkTabs, 50);
        return;
      }

      // Register listeners.
      registerListeners(tabs);

      // Set the active tab (if any).
      var activeTab = $location.search()['tab'];
      if (activeTab) {
        changeTab(activeTab);
      }
    };

    var registerListeners = function(tabs) {
      // Listen for scope destruction.
      scope.$on('$destroy', function() {
        disposed = true;
        locationListener && locationListener();
      });

      // Listen for route changes and update the tabs accordingly.
      if (!opt_rememberCookie) {
        locationListener = $rootScope.$on('$routeUpdate', function(){
          if ($location.search()['tab']) {
            changeTab($location.search()['tab']);
          } else {
            resetDefaultTab();
          }
        });
      }

      // Listen for tab changes.
      tabs.on('shown.bs.tab', function (e) {
        // Invoke the callback, if any.
        opt_clickCallback && opt_clickCallback();

        // Update the search location or cookie.
        if (opt_rememberCookie) {
          // TODO: this
        } else {
          var tabName = e.target.getAttribute('data-target').substr(1);
          $rootScope.$apply(function() {
            var isDefaultTab = tabs[0] == e.target;
            var newSearch = $.extend($location.search(), {});
            if (isDefaultTab) {
              delete newSearch['tab'];
            } else {
              newSearch['tab'] = tabName;
            }

            $location.search(newSearch);
          });
        }

        e.preventDefault();
      });
    };

    // Start the checkTabs timer.
    checkTabs();
  };

  return uiService;
}]);
