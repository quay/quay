/**
 * An element which displays and auto-updates the logs from a build.
 */
angular.module('quay').directive('buildLogsView', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-logs-view.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build',
      'useTimestamps': '=useTimestamps',
      'buildUpdated': '&buildUpdated',
      'isSuperUser': '=isSuperUser'
    },
    controller: function($scope, $element, $interval, $sanitize, ansi2html, ViewArray,
                         AngularPollChannel, ApiService, Restangular, UtilService) {

      var repoStatusApiCall = ApiService.getRepoBuildStatus;
      var repoLogApiCall = ApiService.getRepoBuildLogsAsResource;
      if( $scope.isSuperUser ){
        repoStatusApiCall = ApiService.getRepoBuildStatusSuperUser;
        repoLogApiCall = ApiService.getRepoBuildLogsSuperUserAsResource;
      }

      $scope.logEntries = null;
      $scope.currentParentEntry = null;
      $scope.logStartIndex = 0;
      $scope.buildLogsText = '';
      $scope.currentBuild = null;
      $scope.loadError = null;

      $scope.pollChannel = null;

      var appendToTextLog = function(type, message) {
        if (type == 'phase') {
          text = 'Starting phase: ' + message + '\n';
        } else {
          text = message + '\n';
        }

        $scope.buildLogsText += text.replace(new RegExp("\\033\\[[^m]+m"), '');
      };

      var processLogs = function(logs, startIndex, endIndex) {
        if (!$scope.logEntries) { $scope.logEntries = []; }

        // If the start index given is less than that requested, then we've received a larger
        // pool of logs, and we need to only consider the new ones.
        if (startIndex < $scope.logStartIndex) {
          logs = logs.slice($scope.logStartIndex - startIndex);
        }

        for (var i = 0; i < logs.length; ++i) {
          var entry = logs[i];
          var type = entry['type'] || 'entry';
          if (type == 'command' || type == 'phase' || type == 'error') {
            entry['logs'] = ViewArray.create();
            entry['index'] = $scope.logStartIndex + i;

            $scope.logEntries.push(entry);
            $scope.currentParentEntry = entry;
          } else if ($scope.currentParentEntry) {
            $scope.currentParentEntry['logs'].push(entry);
          }

          appendToTextLog(type, entry['message']);
        }

        return endIndex;
      };

      var handleLogsData = function(logsData, callback) {
        // Process the logs we've received.
        $scope.logStartIndex = processLogs(logsData['logs'], logsData['start'], logsData['total']);

        // If the build status is an error, automatically open the last command run.
        var currentBuild = $scope.currentBuild;
        if (currentBuild['phase'] == 'error') {
          for (var i = $scope.logEntries.length - 1; i >= 0; i--) {
            var currentEntry = $scope.logEntries[i];
            if (currentEntry['type'] == 'command') {
              currentEntry['logs'].setVisible(true);
              break;
            }
          }
        }

        // If the build phase is an error or a complete, then we mark the channel
        // as closed.
        callback(currentBuild['phase'] != 'error' && currentBuild['phase'] != 'complete');
      }

      var getBuildStatusAndLogs = function(build, callback) {
        var params = {
          'repository': build.repository.namespace + '/' + build.repository.name,
          'build_uuid': build.id
        };


        repoStatusApiCall(null, params, true).then(function(resp) {
          if (resp.id != $scope.build.id) { callback(false); return; }

          // Call the build updated handler.
          $scope.buildUpdated({'build': resp});

          // Save the current build.
          $scope.currentBuild = resp;

          // Load the updated logs for the build.
          var options = {
            'start': $scope.logStartIndex
          };

          repoLogApiCall(params, true).withOptions(options).get(function(resp) {
            // If we get a logs url back, then we need to make another XHR request to retrieve the
            // data.
            var logsUrl = resp['logs_url'];
            if (logsUrl) {
              $.ajax({
                url: logsUrl,
              }).done(function(r) {
                $scope.$apply(function() {
                  handleLogsData(r, callback);
                });
              }).error(function(xhr) {
                $scope.$apply(function() {
                  if (xhr.status == 0) {
                    UtilService.isAdBlockEnabled(function(result) {
                      $scope.loadError = result ? 'blocked': 'request-failed';
                    });
                  } else {
                    $scope.loadError = 'request-failed';
                  }
                });
              });

              return;
            }

            handleLogsData(resp, callback);
          }, function(resp) {
            if (resp.status == 403) {
              $scope.loadError = 'unauthorized';
            } else {
              $scope.loadError = 'request-failed';
            }
            callback(false);
          });
        }, function() {
          $scope.loadError = 'request-failed';
          callback(false);
        });
      };

      var startWatching = function(build) {
        // Create a new channel for polling the build status and logs.
        var conductStatusAndLogRequest = function(callback) {
          getBuildStatusAndLogs(build, callback);
        };

        // Make sure to cancel any existing watchers first.
        stopWatching();

        // Register a new poll channel to start watching.
        $scope.pollChannel = AngularPollChannel.create($scope, conductStatusAndLogRequest, 5 * 1000 /* 5s */);
        $scope.pollChannel.start();
      };

      var stopWatching = function() {
        if ($scope.pollChannel) {
          $scope.pollChannel.stop();
          $scope.pollChannel = null;
        }
      };

      $scope.$watch('useTimestamps', function() {
        if (!$scope.logEntries) { return; }
        $scope.logEntries = $scope.logEntries.slice();
      });

      $scope.$watch('build', function(build) {
        if (build) {
          startWatching(build);
        } else {
          stopWatching();
        }
      });

      $scope.hasLogs = function(container) {
        return container.logs.hasEntries;
      };

      $scope.formatDatetime = function(datetimeString) {
        // Note: The standard format required by the Date constructor in JS is
        // "2011-10-10T14:48:00" for date-times. The date-time string we get is exactly that,
        // but with a space instead of a 'T', so we just replace it.
        var dt = new Date(datetimeString.replace(' ', 'T'));
        return dt.toLocaleString();
      }

      $scope.processANSI = function(message, container) {
        var filter = container.logs._filter = (container.logs._filter || ansi2html.create());

        // Note: order is important here.
        var setup = filter.getSetupHtml();
        var stream = filter.addInputToStream(message || '');
        var teardown = filter.getTeardownHtml();
        return setup + stream + teardown;
      };
    }
  };
  return directiveDefinitionObject;
});
