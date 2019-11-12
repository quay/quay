angular.module("angular-tour", [])
  .provider('AngularTour', function() {
    this.$get = ['$document', '$rootScope', '$compile', '$location', function($document, $rootScope, $compile, $location) {
      $rootScope.angular_tour_current = null;

      function _start(tour, opt_stepIndex, opt_existingScope) {
        tour.initialStep = opt_stepIndex || tour.initialStep || 0;
        tour.tourScope = opt_existingScope || null;
        $rootScope.angular_tour_current = tour;
      }

      function _stop() {
        $rootScope.angular_tour_current = null;
      }

      return {
        start: _start,
        stop: _stop
      };
    }];
  })

  .directive('angularTourUi', function() {
    var directiveDefinitionObject = {
      priority: 0,
      templateUrl: '/static/directives/angular-tour-ui.html',
      replace: false,
      transclude: false,
      restrict: 'C',
      scope: {
        'tour': '=tour',
        'inline': '=inline',
      },
      controller: function($rootScope, $scope, $element, $location, $interval, AngularTour) {
        $scope.supported = !!window.EventSource;

        var createNewScope = function(initialScope) {
          var tourScope = jQuery.extend({}, initialScope || {});
          tourScope['_replaceData'] = function(s) {
            if (typeof s != 'string') {
              return s;
            }

            for (var key in tourScope) {
              if (key[0] == '_') { continue; }
              if (tourScope.hasOwnProperty(key)) {
                s = s.replace('{{' + key + '}}', tourScope[key]);
              }
            }
            return s;
          };

          return tourScope;
        };

        $scope.stepIndex = 0;
        $scope.step = null;
        $scope.interval = null;
        $scope.tourScope = null;

        var getElement = function() {
          if (typeof $scope.step['element'] == 'function') {
            return $($scope.step['element'](tourScope));
          }

          return $($scope.tourScope._replaceData($scope.step['element']));
        };

        var checkSignal = function() {
          return $scope.step['signal'] && $scope.step['signal']($scope.tourScope);
        };

        var teardownSignal = function() {
          if (!$scope.step) { return; }

          var signal = $scope.step['signal'];
          if (signal && signal.$teardown) {
            signal.$teardown($scope.tourScope);
          }
        };

        var setupSignal = function() {
          if (!$scope.step) { return; }

          var signal = $scope.step['signal'];
          if (signal && signal.$setup) {
            signal.$setup($scope.tourScope);
          }
        };

        var checkSignalTimer = function() {
          if (!$scope.step || !$scope.tourScope) {
            stopSignalTimer();
            return;
          }

          if (checkSignal()) {
            $scope.next();
          }
        };

        var stopSignalTimer = function() {
          if (!$scope.interval) { return; }

          $interval.cancel($scope.interval);
          $scope.interval = null;
        };

        var startSignalTimer = function() {
          $scope.interval = $interval(checkSignalTimer, 500);
        };

        var closeDomHighlight = function() {
          if (!$scope.step) { return; }

          var element = getElement($scope.tourScope);
          element.spotlight('close');
        };

        var updateDomHighlight = function() {
          var element = getElement();
          if (!element.length) {
            return;
          }

          element.spotlight({
	          opacity: .5,
	          speed: 400,
	          color: '#333',
	          animate: true,
	          easing: 'linear',
	          exitEvent: 'mouseenter',
            exitEventAppliesToElement: true,
            paddingX: 1,
            paddingY: 1
          });
        };

        var fireMixpanelEvent = function() {
          if (!$scope.step || !window['mixpanel']) { return; }

          var eventName = $scope.step['mixpanelEvent'];
          if (eventName) {
            mixpanel.track(eventName);
          }
        };

        $scope.setStepIndex = function(stepIndex) {
          // Close existing spotlight and signal timer.
          teardownSignal();
          closeDomHighlight();
          stopSignalTimer();

          // Check if there is a next step.
          if (!$scope.tour || stepIndex >= $scope.tour.steps.length) {
            $scope.step = null;
            $scope.hasNextStep = false;
            return;
          }

          $scope.step = $scope.tour.steps[stepIndex];
          if ($scope.step.skip) {
            $scope.setStepIndex(stepIndex + 1);
            return;
          }

          fireMixpanelEvent();

          // If the signal is already true, then skip this step entirely.
          setupSignal();
          if (checkSignal()) {
            $scope.setStepIndex(stepIndex + 1);
            return;
          }

          $scope.stepIndex = stepIndex;
          $scope.hasNextStep = stepIndex < $scope.tour.steps.length - 1;

          // Need the timeout here to ensure the click event does not
          // hide the spotlight, and it has to be longer than the hide
          // spotlight animation timing.
          setTimeout(function() {
            updateDomHighlight();
          }, 500);

          // Start listening for signals to move the tour forward.
          if ($scope.step.signal) {
            startSignalTimer();
          }
        };

        $scope.stop = function() {
          closeDomHighlight();
          $scope.tour = null;
          AngularTour.stop();
        };

        $scope.next = function() {
          $scope.setStepIndex($scope.stepIndex + 1);
        };

        $scope.$watch('tour', function(tour) {
          stopSignalTimer();
          if (tour) {
            // Set the tour scope.
            if (tour.tourScope) {
              $scope.tourScope = tour.tourScope;
            } else {
              $scope.tourScope = $scope.tour.tourScope = createNewScope(tour.initialScope);
            }

            // Set the initial step.
            $scope.setStepIndex(tour.initialStep || 0);
          }
        });

        // If this is an inline tour, then we need to monitor the page to determine when
        // to transition it to an overlay tour.
        if ($scope.inline) {
          var counter = 0;
          var unbind = $rootScope.$watch(function() {
            return $location.path();
          }, function(location) {
            // Since this callback fires for the first page display, we only unbind it
            // after the second call.
            if (counter == 1) {
              // Unbind the listener.
              unbind();

              // Teardown any existing signal listener.
              teardownSignal();

              // If there is an active tour, transition it over to the overlay.
              if ($scope.tour && $scope.step && $scope.step['overlayable']) {
                AngularTour.start($scope.tour, $scope.stepIndex + 1, $scope.tourScope);
                $scope.tour = null;
              }
            }
            counter++;
          });
        }
      }
    };
    return directiveDefinitionObject;
  })

  .factory('AngularTourSignals', ['$location', function($location) {
    var signals = {};

    // Signal: When the page location matches the given path.
    signals.matchesLocation = function(locationPath) {
      return function(tourScope) {
        return $location.path() == tourScope._replaceData(locationPath);
      };
    };

    // Signal: When an element is visible in the page's DOM.
    signals.elementVisible = function(elementPath) {
      return function(tourScope) {
        return $(tourScope._replaceData(elementPath)).height() > 0;
      };
    };

    // Signal: When an element is found in the page's DOM.
    signals.elementAvaliable = function(elementPath) {
      return function(tourScope) {
        return $(tourScope._replaceData(elementPath)).length > 0;
      };
    };

    // Signal: When a server-side event matches the predicate.
    signals.serverEvent = function(url, matcher) {
      var checker = function(tourScope) {
        return checker.$message && matcher(checker.$message, tourScope);
      };

      checker.$message = null;

      checker.$setup = function(tourScope) {
        if (!window.EventSource) {
          return;
        }

        var fullUrl = tourScope._replaceData(url);
        checker.$source = new EventSource(fullUrl);
        checker.$source.onmessage = function(e) {
          var parsed = JSON.parse(e.data);
          if (!parsed['data']) {
            return;
          }

          checker.$message = parsed;
        };

        checker.$source.onopen = function(e) {
          checker.$hasError = false;
        };

        checker.$source.onerror = function(e) {
          checker.$hasError = true;
        };
      };

      checker.$teardown = function() {
        if (checker.$source) {
          checker.$source.close();
        }
      };

      return checker;
    };

    return signals;
  }]);
