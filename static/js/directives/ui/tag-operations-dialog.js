/**
 * An element which adds a series of dialogs for performing operations for tags (adding, moving
 * deleting).
 */
angular.module('quay').directive('tagOperationsDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/tag-operations-dialog.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'repository': '=repository',
      'repositoryTags': '=repositoryTags',
      'actionHandler': '=actionHandler',
      'tagChanged': '&tagChanged',
      'labelsChanged': '&labelsChanged'
    },
    controller: function($scope, $element, $timeout, ApiService) {
      $scope.addingTag = false;
      $scope.changeTagsExpirationInfo = null;

      var reloadTags = function(page, tags, added, removed) {
        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'limit': 100,
          'page': page,
          'onlyActiveTags': true
        };

        ApiService.listRepoTags(null, params).then(function(resp) {
          var newTags = resp.tags.reduce(function(result, item, index, array) {
            var tag_name = item['name'];
            result[tag_name] = item;
            return result;
          }, {});

          $.extend(tags, newTags);

          if (resp.has_additional) {
            reloadTags(page + 1, tags, added, removed);
          } else {
            $scope.repositoryTags = tags;

            $timeout(function() {
              $scope.tagChanged({
                'data': { 'added': added, 'removed': removed }
              });
            }, 1);
          }
        });
      };

      var markChanged = function(added, removed) {
        // Reload the tags
        tags = {};
        reloadTags(1, tags, added, removed);
      };

      $scope.alertOnTagOpsDisabled = function() {
        if ($scope.repository.tag_operations_disabled) {
          $('#tagOperationsDisabledModal').modal('show');
          return true;
        }

        return false;
      };

      $scope.isAnotherImageTag = function(image, tag) {
        if (!$scope.repositoryTags) { return; }

        var found = $scope.repositoryTags[tag];
        if (found == null) { return false; }
        return found.image_id != image;
      };

      $scope.isOwnedTag = function(image, tag) {
        if (!$scope.repositoryTags) { return; }

        var found = $scope.repositoryTags[tag];
        if (found == null) { return false; }
        return found.image_id == image;
      };

      $scope.createOrMoveTag = function(image, tag, opt_manifest_digest) {
        if (!$scope.repository.can_write) { return; }
        if ($scope.alertOnTagOpsDisabled()) {
          return;
        }

        $scope.addingTag = true;

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'tag': tag
        };

        var data = {};
        if (image) {
          data['image'] = image;
        }

        if (opt_manifest_digest) {
          data['manifest_digest'] = opt_manifest_digest;
        }

        var errorHandler = ApiService.errorDisplay('Cannot create or move tag', function(resp) {
          $element.find('#createOrMoveTagModal').modal('hide');
        });

        ApiService.changeTag(data, params).then(function(resp) {
          $element.find('#createOrMoveTagModal').modal('hide');
          $scope.addingTag = false;
          markChanged([tag], []);
        }, errorHandler);
      };

      $scope.changeTagsExpiration = function(tags, expiration_date, callback) {
        if (!$scope.repository.can_write) { return; }

        var count = tags.length;
        var perform = function(index) {
          if (index >= count) {
            callback(true);
            markChanged(tags, []);
            return;
          }

          var tag_info = tags[index];
          if (!tag_info) { return; }

          $scope.changeTagExpiration(tag_info.name, expiration_date, function(result) {
            if (!result) {
              callback(false);
              return;
            }

            perform(index + 1);
          }, true);
        };

        perform(0);
      };

      $scope.changeTagExpiration = function(tag, expiration_date, callback) {
        if (!$scope.repository.can_write) { return; }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'tag': tag
        };

        var data = {
          'expiration': expiration_date
        };

        var errorHandler = ApiService.errorDisplay('Cannot change tag expiration', callback);
        ApiService.changeTag(data, params).then(function() {
          callback(true);
        }, errorHandler);
      };

      $scope.deleteMultipleTags = function(tags, callback) {
        if (!$scope.repository.can_write) { return; }

        var count = tags.length;
        var perform = function(index) {
          if (index >= count) {
            callback(true);
            markChanged([], tags);
            return;
          }

          var tag_info = tags[index];
          if (!tag_info) { return; }

          $scope.deleteTag(tag_info.name, function(result) {
            if (!result) {
              callback(false);
              return;
            }

            perform(index + 1);
          }, true);
        };

        perform(0);
      };

      $scope.deleteTag = function(tag, callback, opt_skipmarking) {
        if (!$scope.repository.can_write) { return; }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'tag': tag
        };

        var errorHandler = ApiService.errorDisplay('Cannot delete tag', callback);
        ApiService.deleteFullTag(null, params).then(function() {
          callback(true);
          !opt_skipmarking && markChanged([], [tag]);
        }, errorHandler);
      };

      $scope.restoreTag = function(tag, image_id, opt_manifest_digest, callback) {
        if (!$scope.repository.can_write) { return; }

        var params = {
          'repository': $scope.repository.namespace + '/' + $scope.repository.name,
          'tag': tag.name
        };

        var data = {
          'image': image_id
        };

        if (opt_manifest_digest) {
          data['manifest_digest'] = opt_manifest_digest;
        }

        var errorHandler = ApiService.errorDisplay('Cannot restore tag', callback);
        ApiService.restoreTag(data, params).then(function() {
          callback(true);
          markChanged([], [tag]);
        }, errorHandler);
      };

      $scope.getFormattedTimespan = function(seconds) {
        if (!seconds) {
          return null;
        }
        return moment.duration(seconds, "seconds").humanize();
      };

      $scope.editLabels = function(info, callback) {
        var actions = [];
        var existingMutableLabels = {};

        // Build the set of adds and deletes.
        info['updated_labels'].forEach(function(label) {
          if (label['id']) {
            existingMutableLabels[label['id']] = true;
          } else {
            actions.push({
              'action': 'add',
              'label': label
            });
          }
        });

        info['mutable_labels'].forEach(function(label) {
          if (!existingMutableLabels[label['id']]) {
            actions.push({
              'action': 'delete',
              'label': label
            });
          }
        });

        // Execute the add and delete label actions.
        var currentIndex = 0;

        var performAction = function() {
          if (currentIndex >= actions.length) {
            $scope.labelsChanged({'manifest_digest': info['manifest_digest']});
            callback(true);
            return;
          }

          var currentAction = actions[currentIndex];
          currentIndex++;

          var errorHandler = ApiService.errorDisplay('Could not update labels', callback);
          switch (currentAction.action) {
            case 'add':
              var params = {
                'repository': $scope.repository.namespace + '/' + $scope.repository.name,
                'manifestref': info['manifest_digest']
              };

              var pieces = currentAction['label']['keyValue'].split('=', 2);

              var data = {
                'key': pieces[0],
                'value': pieces[1],
                'media_type': null // Have backend infer the media type
              };

              ApiService.addManifestLabel(data, params).then(performAction, errorHandler);
              break;

            case 'delete':
              var params = {
                'repository': $scope.repository.namespace + '/' + $scope.repository.name,
                'manifestref': info['manifest_digest'],
                'labelid': currentAction['label']['id']
              };

              ApiService.deleteManifestLabel(null, params).then(performAction, errorHandler);
              break;
          }
        };

        performAction();
      };

      var filterLabels = function(labels, readOnly) {
        if (!labels) { return []; }

        return labels.filter(function(label) {
          return (label['source_type'] != 'api') == readOnly;
        });
      };

      $scope.actionHandler = {
        'askDeleteTag': function(tag) {
          if ($scope.alertOnTagOpsDisabled()) {
            return;
          }

          $scope.deleteTagInfo = {
            'tag': tag
          };
        },

        'askDeleteMultipleTags': function(tags) {
          if ($scope.alertOnTagOpsDisabled()) {
            return;
          }

          $scope.deleteMultipleTagsInfo = {
            'tags': tags
          };
        },

        'askAddTag': function(image, opt_manifest_digest) {
          if ($scope.alertOnTagOpsDisabled()) {
            return;
          }

          $scope.tagToCreate = '';
          $scope.toTagImage = image;
          $scope.toTagManifestDigest = opt_manifest_digest;
          $scope.addingTag = false;
          $scope.addTagForm.$setPristine();
          $element.find('#createOrMoveTagModal').modal('show');
        },

        'showLabelEditor': function(manifest_digest) {
          $scope.editLabelsInfo = {
            'manifest_digest': manifest_digest,
            'loading': true
          };

          var params = {
            'repository': $scope.repository.namespace + '/' + $scope.repository.name,
            'manifestref': manifest_digest
          };

          ApiService.listManifestLabels(null, params).then(function(resp) {
            var labels = resp['labels'];

            $scope.editLabelsInfo['readonly_labels'] = filterLabels(labels, true);
            $scope.editLabelsInfo['mutable_labels'] = filterLabels(labels, false);

            $scope.editLabelsInfo['labels'] = labels;
            $scope.editLabelsInfo['loading'] = false;

          }, ApiService.errorDisplay('Could not load manifest labels'));
        },

        'askChangeTagsExpiration': function(tags) {
          if ($scope.alertOnTagOpsDisabled()) {
            return;
          }

          var expiration_date = null;
          expiration_date = tags[0].expiration_date ? tags[0].expiration_date / 1000 : null;
          $scope.changeTagsExpirationInfo = {
            'tags': tags,
            'expiration_date': expiration_date
          };
        },

        'askRestoreTag': function(tag, image_id, opt_manifest_digest) {
          if ($scope.alertOnTagOpsDisabled()) {
            return;
          }

          $scope.restoreTagInfo = {
            'tag': tag,
            'image_id': image_id,
            'manifest_digest': opt_manifest_digest
          };

          $element.find('#restoreTagModal').modal('show');
        }
      };
    }
  };
  return directiveDefinitionObject;
});
