/**
 * An element which displays its contents wrapped in an <a> tag, but only if the href is not null.
 */
angular.module('quay').directive('repoTagHistory', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-tag-history.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'repositoryTags': '=repositoryTags',
      'filter': '=filter',
      'isEnabled': '=isEnabled',
    },
    controller: function($scope, $element, ApiService, StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();
      $scope.tagHistoryData = null;
      $scope.tagHistoryLeaves = {};

      $scope.options = {
        'showFuture': false
      };

      // A delete followed by a create of a tag within this threshold is considered a move.
      var MOVE_THRESHOLD = 2;

      var loadTimeline = function() {
        if (!$scope.repository || !$scope.isEnabled) { return; }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        ApiService.listRepoTags(null, params).then(function(resp) {
          $scope.cachedFullTags = resp.tags;
          processTags(resp.tags);
        });
      };

      $scope.$watch('isEnabled', loadTimeline);
      $scope.$watch('repositoryTags', loadTimeline);
      $scope.$watch('options.showFuture', function() {
        if (!$scope.cachedFullTags) { return; }
        processTags($scope.cachedFullTags);
      });

      var processTags = function(tags) {
        var entries = [];
        var tagEntries = {};

        // For each tag, turn the tag into create, move, delete, restore, etc entries.
        tags.forEach(function(tag) {
          var tagName = tag.name;
          var dockerImageId = tag.docker_image_id;
          var manifestDigest = tag.manifest_digest;

          if (!tagEntries[tagName]) {
            tagEntries[tagName] = [];
          }

          var removeEntry = function(entry) {
            entries.splice(entries.indexOf(entry), 1);
            tagEntries[entry.tag_name].splice(tagEntries[entry.tag_name].indexOf(entry), 1);
          };

          var addEntry = function(action, time, opt_docker_id, opt_old_docker_id,
                                  opt_manifest_digest, opt_old_manifest_digest) {
            var entry = {
              'tag': tag,
              'tag_name': tagName,
              'action': action,
              'start_ts': tag.start_ts,
              'end_ts': tag.end_ts,
              'reversion': tag.reversion,
              'time': time * 1000, // JS expects ms, not s since epoch.
              'docker_image_id': opt_docker_id || dockerImageId,
              'old_docker_image_id': opt_old_docker_id || '',
              'manifest_digest': opt_manifest_digest || manifestDigest,
              'old_manifest_digest': opt_old_manifest_digest || null
            };

            if (!$scope.options.showFuture && time && (time * 1000) >= new Date().getTime()) {
              return;
            }
  
            tagEntries[tagName].push(entry);
            entries.push(entry);
          };

          // If the tag has an end time, it was either deleted or moved.
          if (tag.end_ts) {
            // If a future entry exists with a start time "equal" to the end time for this tag,
            // then the action was a move, rather than a delete and a create.
            var currentEntries = tagEntries[tagName];
            var futureEntry = currentEntries.length > 0 ? currentEntries[currentEntries.length - 1] : {};

            if (futureEntry.start_ts - tag.end_ts <= MOVE_THRESHOLD) {
              removeEntry(futureEntry);
              addEntry(futureEntry.reversion ? 'revert': 'move', tag.end_ts,
                       futureEntry.docker_image_id, dockerImageId, futureEntry.manifest_digest,
                       manifestDigest);
            } else {
              addEntry('delete', tag.end_ts)
            }
          }

          // If the tag has a start time, it was created.
          if (tag.start_ts) {
            addEntry(tag.reversion ? 'recreate' : 'create', tag.start_ts);
          }
        });

        // Sort the overall entries by datetime descending.
        entries.sort(function(a, b) {
          return b.time - a.time;
        });

        // Sort the tag entries by datetime descending.
        Object.keys(tagEntries).forEach(function(name) {
          var te = tagEntries[name];
          te.sort(function(a, b) {
            return b.time - a.time;
          });
        });

        // Add date dividers in.
        for (var i = entries.length - 1; i >= 1; --i) {
          var current = entries[i];
          var next = entries[i - 1];

          if (new Date(current.time).getDate() != new Date(next.time).getDate()) {
            entries.splice(i, 0, {
              'date_break': true,
              'date': new Date(current.time)
            });
          }
        }

        // Add the top-level date divider.
        if (entries.length > 0) {
          entries.splice(0, 0, {
            'date_break': true,
            'date': new Date(entries[0].time)
          });
        }

        $scope.historyEntries = entries;
        $scope.historyEntryMap = tagEntries;
      };

      $scope.isCurrent = function(entry) {
        return $scope.historyEntryMap[entry.tag_name][0] == entry;
      };

      $scope.askRestoreTag = function(entity, use_current_id) {
        if ($scope.repository.can_write) {
          var docker_id = use_current_id ? entity.docker_image_id : entity.old_docker_image_id;
          var digest = use_current_id ? entity.manifest_digest : entity.old_manifest_digest;
          $scope.tagActionHandler.askRestoreTag(entity.tag, docker_id, digest);
        }
      };

      $scope.isFuture = function(entry) {
        if (!entry) { return false; }
        return entry.time >= new Date().getTime();
      };

      $scope.getEntryClasses = function(entry, historyFilter) {
        if (!entry.action) { return ''; }

        var classes = entry.action + ' ';
        if ($scope.historyEntryMap[entry.tag_name][0] == entry) {
          classes += ' current ';
        }

        if ($scope.isFuture(entry)) {
          classes += ' future ';
        }

        if (!historyFilter || !entry.action) {
          return classes;
        }

        var parts = (historyFilter || '').split(',');
        var isMatch = parts.some(function(part) {
          if (part && entry.tag_name) {
            isMatch = entry.tag_name.indexOf(part) >= 0;
            isMatch = isMatch || entry.docker_image_id.indexOf(part) >= 0;
            isMatch = isMatch || entry.old_docker_image_id.indexOf(part) >= 0;
            return isMatch;
          }
        });

        classes += isMatch ? 'filtered-match' : 'filtered-mismatch';
        return classes;
      };
    }
  };
  return directiveDefinitionObject;
});
