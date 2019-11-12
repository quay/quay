angular.module("core-ui", [])
  .factory('CoreDialog', [function() {
    var service = {};
    service['fatal'] = function(title, message) {
      bootbox.dialog({
        "title": title,
        "message": "<div class='alert-icon-container-container'><div class='alert-icon-container'><div class='alert-icon'></div></div></div>" + message,
        "buttons": {},
        "className": "co-dialog fatal-error",
        "closeButton": false
      });
    };

    return service;
  }])

  .directive('corLogBox', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-log-box.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {
        'logs': '=logs'
      },
      controller: function($rootScope, $scope, $element, $timeout) {
        $scope.hasNewLogs = false;

        var scrollHandlerBound = false;
        var isAnimatedScrolling = false;
        var isScrollBottom = true;

        var scrollHandler = function() {
          if (isAnimatedScrolling) { return; }
          var element = $element.find("#co-log-viewer")[0];
          isScrollBottom = element.scrollHeight - element.scrollTop === element.clientHeight;
          if (isScrollBottom) {
            $scope.hasNewLogs = false;
          }
        };

        var animateComplete = function() {
          isAnimatedScrolling = false;
        };

        $scope.moveToBottom = function() {
          $scope.hasNewLogs = false;
          isAnimatedScrolling = true;
          isScrollBottom = true;

          $element.find("#co-log-viewer").animate(
            { scrollTop: $element.find("#co-log-content").height() }, "slow", null, animateComplete);
        };

        $scope.$watch('logs', function(value, oldValue) {
          if (!value) { return; }

          $timeout(function() {
            if (!scrollHandlerBound) {
              $element.find("#co-log-viewer").on('scroll', scrollHandler);
              scrollHandlerBound = true;
            }

            if (!isScrollBottom) {
              $scope.hasNewLogs = true;
              return;
            }

            $scope.moveToBottom();
          }, 500);
        });
      }
    };
    return directiveDefinitionObject;
  })

  .directive('corOptionsMenu', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-options-menu.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {},
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

  .directive('corOption', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-option.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {
        'optionClick': '&optionClick'
      },
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })


  .directive('corTitle', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-title.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {},
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

  .directive('corTitleAction', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-title-action.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {},
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

  .directive('corTitleContent', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-title-content.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {},
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

  .directive('corTitleLink', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-title-link.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {},
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

  .directive('corConfirmDialog', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-confirm-dialog.html',
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'dialogTitle': '@dialogTitle',
        'dialogActionTitle': '@dialogActionTitle',
        'dialogForm': '=dialogForm',
        'dialogButtonClass': '@dialogButtonClass',

        'dialogContext': '=dialogContext',
        'dialogAction': '&dialogAction'
      },

      controller: function($rootScope, $scope, $element) {
        $scope.working = false;

        $scope.$watch('dialogContext', function(dc) {
          if (!dc) { return; }
          $scope.show();
        });

        $scope.performAction = function() {
          $scope.working = true;
          $scope.dialogAction({
            'info': $scope.dialogContext,
            'callback': function(result) {
              $scope.hide();
            }
          });
        };

        $scope.show = function() {
          if ($scope.dialogForm) {
            $scope.dialogForm.$setPristine();
          }

          $scope.working = false;
          $element.find('.modal').modal({});
        };

        $scope.hide = function() {
          $element.find('.modal').modal('hide');
        };
      }
    };
    return directiveDefinitionObject;
  })

 .directive('corFloatingBottomBar', function() {
    var directiveDefinitionObject = {
      priority: 3,
      templateUrl: '/static/directives/cor-floating-bottom-bar.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {},
      controller: function($rootScope, $scope, $element, $timeout, $interval) {
        var handler = function() {
          $element.removeClass('floating');
          $element.css('width', $element[0].parentNode.clientWidth + 'px');

          var windowHeight = $(window).height();
          var rect = $element[0].getBoundingClientRect();
          if (rect.bottom > windowHeight) {
            $element.addClass('floating');
          }
        };

        $(window).on("scroll", handler);
        $(window).on("resize", handler);

        var previousHeight = $element[0].parentNode.clientHeight;
        var stop = $interval(function() {
          var currentHeight = $element[0].parentNode.clientWidth;
          if (previousHeight != currentHeight) {
            currentHeight = previousHeight;
            handler();
          }
        }, 100);

        $scope.$on('$destroy', function() {
          $(window).off("resize", handler);
          $(window).off("scroll", handler);
          $interval.cancel(stop);
        });
      }
    };
    return directiveDefinitionObject;

 })

  .directive('corLoaderInline', function() {
      var directiveDefinitionObject = {
        templateUrl: '/static/directives/cor-loader-inline.html',
        replace: true,
        restrict: 'C',
        scope: {
        },
        controller: function($rootScope, $scope, $element) {
        }
      };
      return directiveDefinitionObject;
  })

  .directive('corLoader', function() {
      var directiveDefinitionObject = {
        templateUrl: '/static/directives/cor-loader.html',
        replace: true,
        restrict: 'C',
        scope: {
        },
        controller: function($rootScope, $scope, $element) {
        }
      };
      return directiveDefinitionObject;
  })

 .directive('corStep', function() {
    var directiveDefinitionObject = {
      priority: 4,
      templateUrl: '/static/directives/cor-step.html',
      replace: true,
      transclude: false,
      requires: '^corStepBar',
      restrict: 'C',
      scope: {
        'icon': '@icon',
        'title': '@title',
        'text': '@text'
      },
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

 .directive('corProgressBar', function() {
    var directiveDefinitionObject = {
      priority: 4,
      templateUrl: '/static/directives/cor-progress-bar.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      scope: {
        'progress': '=progress'
      },
      controller: function($rootScope, $scope, $element) {
      }
    };
    return directiveDefinitionObject;
  })

 .directive('corCheckableMenu', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-checkable-menu.html',
      replace: false,
      transclude: true,
      restrict: 'C',
      scope: {
        'controller': '=controller',
        'filter': '=?filter'
      },
      controller: function($rootScope, $scope, $element) {
        $scope.getClass = function(items, checked) {
          if (!checked) {
            return 'none';
          }

          if (checked.length == 0) {
            return 'none';
          }

          if (checked.length == items.length) {
            return 'all';
          }

          return 'some';
        };

        $scope.toggleItems = function($event) {
          $event.stopPropagation();
          if ($scope.controller) {
            $scope.controller.toggleItems($scope.filter);
          }
        };

        this.checkByFilter = function(filter) {
          if ($scope.controller) {
            $scope.controller.checkByFilter(function(item) {
              return filter({'item': item});
            }, $scope.filter);
          }
        };
      }
    };
    return directiveDefinitionObject;
  })

 .directive('corCheckableMenuItem', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-checkable-menu-item.html',
      replace: true,
      transclude: true,
      restrict: 'C',
      require: '^corCheckableMenu',
      scope: {
        'itemFilter': '&itemFilter'
      },
      link: function($scope, $element, $attr, parent) {
        $scope.parent = parent;
      },

      controller: function($rootScope, $scope, $element) {
        $scope.selected = function() {
          $scope.parent.checkByFilter(this.itemFilter);
        };
      }
    };
    return directiveDefinitionObject;
  })

 .directive('corCheckableItem', function() {
    var directiveDefinitionObject = {
      priority: 1,
      templateUrl: '/static/directives/cor-checkable-item.html',
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'item': '=item',
        'controller': '=controller'
      },
      controller: function($rootScope, $scope, $element) {
        $scope.toggleItem = function($event) {
          $event.preventDefault();
          $event.stopPropagation();
          $scope.controller.toggleItem($scope.item, $event.shiftKey);
        };
      }
    };
    return directiveDefinitionObject;
  })

 .directive('corTable', function() {
  var directiveDefinitionObject = {
    priority: 1,
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {},
    compile: function(tElement, tAttrs, transclude) {
      if (!window.matchMedia('(max-width: 767px)').matches) {
        return;
      }

      var cloneWithAttr = function(e, kind, opt_fullclone) {
        var clone = $(document.createElement(kind));
        var attributes = $(e).prop("attributes");
        $.each(attributes, function() {
          clone.attr(this.name, this.value);
        });

        if (opt_fullclone) {
          for (var i = 0; i < e.childNodes.length; ++i) {
            clone.append($(e.childNodes[i]).clone(true));
          }
        }

        return clone;
      };

      var appendRepeater = function(div, tr, headers, includeRepeat) {
        // Find all the tds directly under the tr and convert into a header + value span.
        tr.children('td').each(function(idx, td) {
          var displayer = cloneWithAttr(tr, 'div');

          if (!includeRepeat) {
            displayer.removeAttr('ng-repeat');
          }

          if (idx < headers.length) {
            displayer.append(headers[idx].clone(true).addClass('mobile-col-header'));
          }

          displayer.append(cloneWithAttr(td, 'div', true).addClass('mobile-col-value'));
          div.append(displayer);
        });
      };

      // Find the thead's tds and turn them into header elements.
      var headers = [];
      tElement.find('thead td').each(function(idx, td) {
        headers.push(cloneWithAttr(td, 'div', true));
      });

      // Find the element with the 'ng-repeat'.
      var repeater = tElement.find('[ng-repeat]')[0];

      // Convert the repeater into a <div> repeater.
      var divRepeater = cloneWithAttr(repeater, 'div').addClass('mobile-row');

      // If the repeater is a tbody, then we append each child tr. Otherwise, the repeater
      // itself should be a tr.
      if (repeater.nodeName.toLowerCase() == 'tbody') {
        $(repeater).children().each(function(idx, tr) {
          appendRepeater(divRepeater, $(tr), headers, true);
        });
      } else {
        appendRepeater(divRepeater, $(repeater), headers, false);
      }

      var repeaterBody = $(document.createElement('tbody'));
      var repeaterTr = $(document.createElement('tr'))
      var repeaterTd = $(document.createElement('td'))

      repeaterTd.append(divRepeater);
      repeaterTr.append(repeaterTd);
      repeaterBody.append(repeaterTr);

      // Remove the tbody and thead.
      tElement.find('thead').remove();
      tElement.find('tbody').remove();
      tElement.append(repeaterBody);
    },

    controller: function($rootScope, $scope, $element) {
      $element.addClass('co-table');
    }
  };
  return directiveDefinitionObject;
});
