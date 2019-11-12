/**
 * An element which displays the builds panel for a repository view.
 */
angular.module('quay').directive('repoPanelBuilds', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-view/repo-panel-builds.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'builds': '=builds',
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, $filter, $routeParams, ApiService, TriggerService, UserService, StateService) {
      StateService.updateStateIn($scope, function(state) {
        $scope.inReadOnlyMode = state.inReadOnlyMode;
      });

      var orderBy = $filter('orderBy');

      $scope.TriggerService = TriggerService;

      UserService.updateUserIn($scope);

      $scope.options = {
        'filter': 'recent',
        'reverse': false,
        'predicate': 'started_datetime'
      };

      $scope.currentFilter = null;

      $scope.currentStartTrigger = null;

      $scope.showBuildDialogCounter = 0;
      $scope.showTriggerStartDialogCounter = 0;

      $scope.triggerCredentialsModalTrigger = null;
      $scope.triggerCredentialsModalCounter = 0;

      $scope.feedback = null;

      var updateBuilds = function() {
        if (!$scope.allBuilds) { return; }

        var unordered = $scope.allBuilds.map(function(build_info) {
          var commit_sha = null;

          if (build_info.trigger_metadata) {
            commit_sha = TriggerService.getCommitSHA(build_info.trigger_metadata);
          }

          return $.extend(build_info, {
            'started_datetime': (new Date(build_info.started)).valueOf() * (-1),
            'building_tags': build_info.tags || [],
            'commit_sha': commit_sha
          });
        });

        $scope.fullBuilds = orderBy(unordered, $scope.options.predicate, $scope.options.reverse);
      };

      var loadBuilds = function(opt_forcerefresh) {
        if (!$scope.builds || !$scope.repository || !$scope.options.filter || !$scope.isEnabled) {
          return;
        }

        // Note: We only refresh if the filter has changed.
        var filter = $scope.options.filter;
        if ($scope.buildsResource && filter == $scope.currentFilter && !opt_forcerefresh) {
          return;
        }

        var since = null;
        var limit = 10;

        if ($scope.options.filter == '48hour') {
          since = Math.floor(moment().subtract(2, 'days').valueOf() / 1000);
          limit = 100;
        } else if ($scope.options.filter == '30day') {
          since = Math.floor(moment().subtract(30, 'days').valueOf() / 1000);
          limit = 100;
        } else {
          since = null;
          limit = 10;
        }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'limit': limit,
          'since': since
        };

        $scope.buildsResource = ApiService.getRepoBuildsAsResource(params).get(function(resp) {
          $scope.allBuilds = resp.builds;
          $scope.currentFilter = filter;
          updateBuilds();
        });
      };

      var buildsChanged = function() {
        if (!$scope.allBuilds) {
          loadBuilds();
          return;
        }

        if (!$scope.builds || !$scope.repository || !$scope.isEnabled) {
          return;
        }

        // Replace any build records with updated records from the server.
        var requireReload = false;
        $scope.builds.map(function(build) {
          var found = false;
          for (var i = 0; i < $scope.allBuilds.length; ++i) {
            var current = $scope.allBuilds[i];
            if (current.id == build.id && current.phase != build.phase) {
              $scope.allBuilds[i] = build;
              found = true;
              break;
            }
          }

          // If the build was not found, then a new build has started. Reload
          // the builds list.
          if (!found) {
            requireReload = true;
          }
        });

        if (requireReload) {
          loadBuilds(/* force refresh */true);
        } else {
          updateBuilds();
        }
      };

      var loadBuildTriggers = function() {
        if (!$scope.repository || !$scope.repository.can_admin || !$scope.isEnabled) { return; }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        $scope.triggersResource = ApiService.listBuildTriggersAsResource(params).get(function(resp) {
          $scope.triggers = resp.triggers;
        });
      };

      $scope.$watch('repository', loadBuildTriggers);
      $scope.$watch('repository', loadBuilds);

      $scope.$watch('isEnabled', loadBuildTriggers);
      $scope.$watch('isEnabled', loadBuilds);

      $scope.$watch('builds', buildsChanged);

      $scope.$watch('options.filter', loadBuilds);
      $scope.$watch('options.predicate', updateBuilds);
      $scope.$watch('options.reverse', updateBuilds);

      $scope.tablePredicateClass = function(name, predicate, reverse) {
        if (name != predicate) {
          return '';
        }

        return 'current ' + (reverse ? 'reversed' : '');
      };

      $scope.orderBy = function(predicate) {
        if (predicate == $scope.options.predicate) {
          $scope.options.reverse = !$scope.options.reverse;
          return;
        }

        $scope.options.reverse = false;
        $scope.options.predicate = predicate;
      };

      $scope.showTriggerCredentialsModal = function(trigger) {
        $scope.triggerCredentialsModalTrigger = trigger;
        $scope.triggerCredentialsModalCounter++;
      };

      $scope.askDeleteTrigger = function(trigger) {
        $scope.deleteTriggerInfo = {
          'trigger': trigger
        };
      };

      $scope.askRunTrigger = function(trigger) {
        if (!trigger.enabled) {
          return;
        }

        if (!trigger.can_invoke) {
          bootbox.alert('You do not have permission to manually invoke this trigger');
          return;
        }

        $scope.currentStartTrigger = trigger;
        $scope.showTriggerStartDialogCounter++;
      };

      $scope.askToggleTrigger = function(trigger) {
        if (!trigger.can_invoke) {
          bootbox.alert('You do not have permission to edit this trigger');
          return;
        }

        $scope.toggleTriggerInfo = {
          'trigger': trigger
        };
      };

      $scope.toggleTrigger = function(trigger, opt_callback) {
        if (!trigger) { return; }
        
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'trigger_uuid': trigger.id
        };

        var data = {
          'enabled': !trigger.enabled
        };

        var errorHandler = ApiService.errorDisplay('Could not toggle build trigger', function() {
          opt_callback && opt_callback(false);
        });

        ApiService.updateBuildTrigger(data, params).then(function(resp) {
          trigger.enabled = !trigger.enabled;
          trigger.disabled_reason = 'user_toggled';
          opt_callback && opt_callback(true);
        }, errorHandler);
      };

      $scope.deleteTrigger = function(trigger, opt_callback) {
        if (!trigger) { return; }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'trigger_uuid': trigger.id
        };

        var errorHandler = ApiService.errorDisplay('Could not delete build trigger', function() {
          opt_callback && opt_callback(false);
        });

        ApiService.deleteBuildTrigger(null, params).then(function(resp) {
          $scope.triggers.splice($scope.triggers.indexOf(trigger), 1);
          opt_callback && opt_callback(true);
        }, errorHandler);
      };

      $scope.showNewBuildDialog = function() {
        $scope.showBuildDialogCounter++;
      };

      $scope.handleBuildStarted = function(build) {
        if ($scope.allBuilds) {
          $scope.allBuilds.push(build);
        }
        updateBuilds();

        $scope.feedback = {
          'kind': 'info',
          'message': 'Build {buildid} started',
          'data': {
            'buildid': build.id
          }
        };
      };
    }
  };
  return directiveDefinitionObject;
});

