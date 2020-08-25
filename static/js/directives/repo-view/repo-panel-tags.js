/**
 * An element which displays the tags panel for a repository view.
 */
angular.module('quay').directive('repoPanelTags', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/repo-view/repo-panel-tags.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'repositoryTags': '=repositoryTags',
      'selectedTags': '=selectedTags',
      'historyFilter': '=historyFilter',
      'imagesResource': '=imagesResource',

      'isEnabled': '=isEnabled',

      'getImages': '&getImages'
    },
    controller: function($scope, $element, $filter, $location, ApiService, UIService,
                         VulnerabilityService, TableService, Features, StateService) {
      StateService.updateStateIn($scope, function(state) {
        $scope.inReadOnlyMode = state.inReadOnlyMode;
      });

      $scope.Features = Features;
      
      $scope.maxTrackCount = 5;

      $scope.checkedTags = UIService.createCheckStateController([], 'name');
      $scope.checkedTags.setPage(0);

      $scope.options = {
        'predicate': 'last_modified_datetime',
        'reverse': false,
        'page': 0
      };

      $scope.iterationState = {};
      $scope.tagActionHandler = null;
      $scope.tagsPerPage = 25;

      $scope.expandedView = false;
      $scope.labelCache = {};

      $scope.manifestVulnerabilities = {};
      $scope.repoDelegationsInfo = null;

      $scope.defcon1 = {};
      $scope.hasDefcon1 = false;

      var loadRepoSignatures = function() {
        if (!$scope.repository || !$scope.repository.trust_enabled) {
          return;
        }

        $scope.repoSignatureError = false;
        $scope.repoDelegationsInfo = null;

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name
        };

        ApiService.getRepoSignatures(null, params).then(function(resp) {
          $scope.repoDelegationsInfo = resp;
        }, function() {
          $scope.repoDelegationsInfo = {'error': true};
        });
      };

      var setTagState = function() {
        if (!$scope.repositoryTags || !$scope.selectedTags) { return; }

        // Build a list of all the tags, with extending information.
        var allTags = [];
        for (var tag in $scope.repositoryTags) {
          if (!$scope.repositoryTags.hasOwnProperty(tag)) { continue; }

          var tagData = $scope.repositoryTags[tag];
          var tagInfo = $.extend(tagData, {
            'name': tag,
            'last_modified_datetime': TableService.getReversedTimestamp(tagData.last_modified),
            'expiration_date': tagData.expiration ? TableService.getReversedTimestamp(tagData.expiration) : null,
          });

          allTags.push(tagInfo);
        }

        // Sort the tags by the predicate and the reverse, and map the information.
        var ordered = TableService.buildOrderedItems(allTags, $scope.options,
            ['name', 'manifest_digest'], ['last_modified_datetime', 'size']).entries;

        var checked = [];
        var manifestMap = {};
        var manifestIndexMap = {};
        var manifestDigests = [];
        for (var i = 0; i < ordered.length; ++i) {
          var tagInfo = ordered[i];
          if (!tagInfo.manifest_digest) {
            continue;
          }

          if (!manifestMap[tagInfo.manifest_digest]) {
            manifestMap[tagInfo.manifest_digest] = [];
            manifestDigests.push(tagInfo.manifest_digest)
          }

          manifestMap[tagInfo.manifest_digest].push(tagInfo);
          if ($.inArray(tagInfo.name, $scope.selectedTags) >= 0) {
            checked.push(tagInfo);
          }

          if (!manifestIndexMap[tagInfo.manifest_digest]) {
            manifestIndexMap[tagInfo.manifest_digest] = {'start': i, 'end': i};
          }

          manifestIndexMap[tagInfo.manifest_digest]['end'] = i;
        };

        // Calculate the image tracks.
        var colors = d3.scale.category10();
        if (Object.keys(manifestMap).length > 10) {
          colors = d3.scale.category20();
        }

        var manifestTracks = [];
        var manifestTrackEntries = [];
        var trackEntryForManifest = {};

        var visibleStartIndex = ($scope.options.page * $scope.tagsPerPage);
        var visibleEndIndex = (($scope.options.page + 1) * $scope.tagsPerPage);

        manifestDigests.sort().map(function(manifest_digest) {
          if (manifestMap[manifest_digest].length >= 2){
            // Create the track entry.
            var manifestIndexRange = manifestIndexMap[manifest_digest];
            var colorIndex = manifestTrackEntries.length;
            var trackEntry = {
              'manifest_digest': manifest_digest,
              'color': colors(colorIndex),
              'count': manifestMap[manifest_digest].length,
              'tags': manifestMap[manifest_digest],
              'index_range': manifestIndexRange,
              'visible': visibleStartIndex <= manifestIndexRange.end && manifestIndexRange.start <= visibleEndIndex,
            };

            trackEntryForManifest[manifest_digest] = trackEntry;
            manifestMap[manifest_digest]['color'] = colors(colorIndex);

            // Find the track in which we can place the entry, if any.
            var existingTrack = null;
            for (var i = 0; i < manifestTracks.length; ++i) {
              // For the current track, ensure that the start and end index
              // for the current entry is outside of the range of the track's
              // entries. If so, then we can add the entry to the track.
              var currentTrack = manifestTracks[i];
              var canAddToCurrentTrack = true;
              for (var j = 0; j < currentTrack.entries.length; ++j) {
                var currentTrackEntry = currentTrack.entries[j];
                var entryInfo = manifestIndexMap[currentTrackEntry.manifest_digest];
                if (Math.max(entryInfo.start, manifestIndexRange.start) <= Math.min(entryInfo.end, manifestIndexRange.end)) {
                  canAddToCurrentTrack = false;
                  break;
                }
              }

              if (canAddToCurrentTrack) {
                existingTrack = currentTrack;
                break;
              }
            }

            // Add the entry to the track or create a new track if necessary.
            if (existingTrack) {
              existingTrack.entries.push(trackEntry)
              existingTrack.entryByManifestDigest[manifest_digest] = trackEntry;
              existingTrack.endIndex = Math.max(existingTrack.endIndex, manifestIndexRange.end);

              for (var j = manifestIndexRange.start; j <= manifestIndexRange.end; j++) {
                existingTrack.entryByIndex[j] = trackEntry;
              }
            } else {
              var entryByManifestDigest = {};
              entryByManifestDigest[manifest_digest] = trackEntry;

              var entryByIndex = {};
              for (var j = manifestIndexRange.start; j <= manifestIndexRange.end; j++) {
                entryByIndex[j] = trackEntry;
              }

              manifestTracks.push({
                'entries': [trackEntry],
                'entryByManifestDigest': entryByManifestDigest,
                'startIndex': manifestIndexRange.start,
                'endIndex': manifestIndexRange.end,
                'entryByIndex': entryByIndex,
              });
            }

            manifestTrackEntries.push(trackEntry);
          }
        });

        $scope.manifestMap = manifestMap;
        $scope.manifestTracks = manifestTracks;
        $scope.manifestTrackEntries = manifestTrackEntries;
        $scope.trackEntryForManifest = trackEntryForManifest;

        $scope.options.page = 0;

        $scope.tags = ordered;
        $scope.allTags = allTags;

        $scope.checkedTags = UIService.createCheckStateController(ordered, 'name');
        $scope.checkedTags.setPage($scope.options.page, $scope.tagsPerPage);

        $scope.checkedTags.listen(function(allChecked, pageChecked) {
          $scope.selectedTags = allChecked.map(function(tag_info) {
            return tag_info.name;
          });

          $scope.fullPageSelected = ((pageChecked.length == $scope.tagsPerPage) &&
                                     (allChecked.length != $scope.tags.length));
          $scope.allTagsSelected = ((allChecked.length > $scope.tagsPerPage) &&
                                    (allChecked.length == $scope.tags.length));
        });

        $scope.checkedTags.setChecked(checked);
      }

      $scope.$watch('options.predicate', setTagState);
      $scope.$watch('options.reverse', setTagState);
      $scope.$watch('options.filter', setTagState);

      $scope.$watch('options.page', function(page) {
        if (page != null && $scope.checkedTags) {
         $scope.checkedTags.setPage(page, $scope.tagsPerPage);
        }
      });

      $scope.$watch('selectedTags', function(selectedTags) {
        if (!selectedTags || !$scope.repository || !$scope.manifestMap) { return; }

        $scope.checkedTags.setChecked(selectedTags.map(function(tag) {
          return $scope.repositoryTags[tag];
        }));
      }, true);

      $scope.$watch('repository', function(updatedRepoObject, previousRepoObject) {
        // Process each of the tags.
        setTagState();
        loadRepoSignatures();
      });

      $scope.$watch('repositoryTags', function(newTags, oldTags) {
        if (newTags === oldTags) { return; }
        // Process each of the tags.
        setTagState();
        loadRepoSignatures();
      }, true);

      $scope.clearSelectedTags = function() {
        $scope.checkedTags.setChecked([]);
      };

      $scope.selectAllTags = function() {
        $scope.checkedTags.setChecked($scope.tags);
      };

      $scope.constrastingColor = function(backgroundColor) {
        // From: https://stackoverflow.com/questions/11068240/what-is-the-most-efficient-way-to-parse-a-css-color-in-javascript
        function parseColor(input) {
          m = input.match(/^#([0-9a-f]{6})$/i)[1];
          return [
            parseInt(m.substr(0,2),16),
            parseInt(m.substr(2,2),16),
            parseInt(m.substr(4,2),16)
          ];
        }

        var rgb = parseColor(backgroundColor);

        // From W3C standard.
        var o = Math.round(((parseInt(rgb[0]) * 299) + (parseInt(rgb[1]) * 587) + (parseInt(rgb[2]) * 114)) / 1000);
        return (o > 150) ? 'black' : 'white';
      };

      $scope.getTrackEntryForIndex = function(it, index) {
        index += $scope.options.page * $scope.tagsPerPage;
        return it.entryByIndex[index];
      };

      $scope.trackLineExpandedClass = function(it, index, track_info) {
        var entry = $scope.getTrackEntryForIndex(it, index);
        if (!entry) {
          return '';
        }

        var adjustedIndex = index + ($scope.options.page * $scope.tagsPerPage);

        if (index < entry.index_range.start) {
          return 'before';
        }

        if (index > entry.index_range.end) {
          return 'after';
        }

        if (index >= entry.index_range.start && index < entry.index_range.end) {
          return 'middle';
        }

        return '';
      };

      $scope.trackLineClass = function(it, index) {
        var entry = $scope.getTrackEntryForIndex(it, index);
        if (!entry) {
          return '';
        }

        var adjustedIndex = index + ($scope.options.page * $scope.tagsPerPage);

        if (index == entry.index_range.start) {
          return 'start';
        }

        if (index == entry.index_range.end) {
          return 'end';
        }

        if (index > entry.index_range.start && index < entry.index_range.end) {
          return 'middle';
        }

        if (index < entry.index_range.start) {
          return 'before';
        }

        if (index > entry.index_range.end) {
          return 'after';
        }
      };

      $scope.tablePredicateClass = function(name, predicate, reverse) {
        if (name != predicate) {
          return '';
        }

        return 'current ' + (reverse ? 'reversed' : '');
      };

      $scope.askDeleteTag = function(tag) {
        $scope.tagActionHandler.askDeleteTag(tag);
      };

      $scope.askDeleteMultipleTags = function(tags) {
        if (tags.length == 1) {
          $scope.askDeleteTag(tags[0].name);
          return;
        }

        $scope.tagActionHandler.askDeleteMultipleTags(tags);
      };

      $scope.askChangeTagsExpiration = function(tags) {
        if ($scope.inReadOnlyMode) {
          return;
        }
        $scope.tagActionHandler.askChangeTagsExpiration(tags);
      };

      $scope.askAddTag = function(tag) {
        if ($scope.inReadOnlyMode) {
          return;
        }
        $scope.tagActionHandler.askAddTag(tag.image_id, tag.manifest_digest);
      };

      $scope.showLabelEditor = function(tag) {
        if ($scope.inReadOnlyMode) {
          return;
        }
        if (!tag.manifest_digest) { return; }
        $scope.tagActionHandler.showLabelEditor(tag.manifest_digest);
      };

      $scope.orderBy = function(predicate) {
        if (predicate == $scope.options.predicate) {
          $scope.options.reverse = !$scope.options.reverse;
          return;
        }

        $scope.options.reverse = false;
        $scope.options.predicate = predicate;
      };

      $scope.commitTagFilter = function(tag) {
        var r = new RegExp('^[0-9a-fA-F]{7}$');
        return tag.name.match(r);
      };

      $scope.allTagFilter = function(tag) {
        return true;
      };

      $scope.noTagFilter = function(tag) {
        return false;
      };

      $scope.manifestDigestFilter = function(manifest_digest, tag) {
        return tag.manifest_digest == manifest_digest;
      };

      $scope.setTab = function(tab) {
        $location.search('tab', tab);
      };

      $scope.selectTrack = function(it) {
        $scope.checkedTags.checkByFilter(function(tag) {
          return $scope.manifestDigestFilter(it.manifest_digest, tag);
        });
      };

      $scope.showHistory = function(checked) {
        if (!checked.length) {
          return;
        }

        $scope.historyFilter = $scope.getTagNames(checked);
        $scope.setTab('history');
      };

      $scope.setExpanded = function(expanded) {
        $scope.expandedView = expanded;
      };

      $scope.getTagNames = function(checked) {
        var names = checked.map(function(tag) {
          return tag.name;
        });

        return names.join(',');
      };

      $scope.handleLabelsChanged = function(manifest_digest) {
        delete $scope.labelCache[manifest_digest];
      };

      $scope.loadManifestList = function(tag) {
        if (tag.manifest_list_loading) {
          return;
        }

        tag.manifest_list_loading = true;

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'manifestref': tag.manifest_digest
        };

        ApiService.getRepoManifest(null, params).then(function(resp) {
          tag.manifest_list = JSON.parse(resp['manifest_data']);
          tag.manifest_list_loading = false;
        }, ApiService.errorDisplay('Could not load manifest list contents'))
      };

      $scope.manifestsOf = function(tag) {
        if (!tag.is_manifest_list) {
          return [];
        }

        if (!tag.manifest_list) {
          $scope.loadManifestList(tag);
          return [];
        }

        if (!tag._mapped_manifests) {
          // Calculate once and cache to avoid angular digest cycles.
          tag._mapped_manifests = tag.manifest_list.manifests.map(function(manifest) {
            return {
              'raw': manifest,
              'os': manifest.platform.os,
              'size': manifest.size,
              'digest': manifest.digest,
              'description': `${manifest.platform.os} on ${manifest.platform.architecture}`,
            };
          });
        }

        return tag._mapped_manifests;
      };
    }
  };
  return directiveDefinitionObject;
});
