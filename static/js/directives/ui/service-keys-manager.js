/**
 * An element which displays a panel for managing keys for external services.
 */
angular.module('quay').directive('serviceKeysManager', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/service-keys-manager.html',
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'isEnabled': '=isEnabled'
    },
    controller: function($scope, $element, $sanitize, ApiService, TableService, UIService,
                         StateService) {
      $scope.inReadOnlyMode = StateService.inReadOnlyMode();

      $scope.options = {
        'filter': null,
        'predicate': 'expiration_datetime',
        'reverse': false,
      };

      $scope.deleteKeysInfo = null;
      $scope.approveKeysInfo = null;
      $scope.changeKeysInfo = null;

      $scope.checkedKeys = UIService.createCheckStateController([], 'kid');

      $scope.TableService = TableService;
      $scope.newKey = null;
      $scope.creatingKey = false;
      $scope.context = {
        'expirationChangeInfo': null
      };

      var buildOrderedKeys = function() {
        if (!$scope.keys) {
          return;
        }

        var keys = $scope.keys.map(function(key) {
          var expiration_datetime = -Number.MAX_VALUE;
          if (key.rotation_duration) {
            expiration_datetime = -(Number.MAX_VALUE/2);
          } else if (key.expiration_date) {
            expiration_datetime = new Date(key.expiration_date).valueOf() * (-1);
          }

          return $.extend(key, {
            'creation_datetime': new Date(key.creation_date).valueOf() * (-1),
            'expiration_datetime': expiration_datetime,
            'expanded': false
          });
        });

        $scope.orderedKeys = TableService.buildOrderedItems(keys, $scope.options,
            ['name', 'kid', 'service'],
            ['creation_datetime', 'expiration_datetime'])

        $scope.checkedKeys = UIService.createCheckStateController($scope.orderedKeys.visibleEntries, 'kid');
      };

      var loadServiceKeys = function() {
        $scope.options.filter = null;
        $scope.now = new Date();
        $scope.keysResource = ApiService.listServiceKeysAsResource().get(function(resp) {
          $scope.keys = resp['keys'];
          buildOrderedKeys();
        });
      };

      $scope.getKeyTitle = function(key) {
        if (!key) { return ''; }
        return key.name || key.kid.substr(0, 12);
      };

      $scope.toggleDetails = function(key) {
        key.expanded = !key.expanded;
      };

      $scope.getRotationDate = function(key) {
        return moment(key.created_date).add(key.rotation_duration, 's').format('LLL');
      };

      $scope.willRotate = function(key) {
        if (!key.expiration_date) {
          return false;
        }

        if (key.rotation_duration) {
          var rotate_date = moment(key.created_date).add(key.rotation_duration, 's')
          if (moment().isBefore(rotate_date)) {
            return true;
          }
        }

        return false;
      };

      $scope.showChangeName = function(key) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        bootbox.prompt({
          'size': 'small',
          'title': 'Enter a friendly name for key ' + $sanitize($scope.getKeyTitle(key)),
          'value': key.name || '',
          'callback': function(value) {
            if (value != null) {
              if (!value.match(/^[\s a-zA-Z0-9\-_:/]*$/)){
                bootbox.alert({
                  'message': 'Invalid friendly name: input does not match <code>^[\\s a-zA-Z0-9\-_:/]*$</code>', 
                  'callback': function(){
                    $scope.showChangeName(key)
                  }
                });

                return
              }

              var data = {
                'name': value
              };

              var params = {
                'kid': key.kid
              };

              ApiService.updateServiceKey(data, params).then(function(resp) {
                loadServiceKeys();
              }, ApiService.errorDisplay('Could not update service key'));
            }
          }
        });
      };

      $scope.showChangeExpiration = function(key) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.context.expirationChangeInfo = {
          'key': key,
          'expiration_date': key.expiration_date ? (new Date(key.expiration_date).getTime() / 1000) : null
        };
      };

      $scope.changeKeyExpiration = function(changeInfo, callback) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        var errorHandler = ApiService.errorDisplay('Could not change expiration on service key', function() {
          loadServiceKeys();
          callback(false);
        });

        var data = {
          'expiration': changeInfo.expiration_date
        };

        var params = {
          'kid': changeInfo.key.kid
        };

        ApiService.updateServiceKey(data, params).then(function(resp) {
          loadServiceKeys();
          callback(true);
        }, errorHandler);
      };

      $scope.createServiceKey = function() {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.creatingKey = true;
        ApiService.createServiceKey($scope.newKey).then(function(resp) {
          $scope.creatingKey = false;
          $('#createKeyModal').modal('hide');
          $scope.createdKey = resp;
          $('#createdKeyModal').modal('show');
          loadServiceKeys();
        }, ApiService.errorDisplay('Could not create service key'));
      };
      
      $scope.updateNewKeyNotes = function(content) {
        $scope.newKey.notes = content;
      };

      $scope.showApproveKey = function(key) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.approvalKeyInfo = {
          'key': key,
          'notes': ''
        };
      };

      $scope.approveKey = function(approvalKeyInfo, callback) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        var errorHandler = ApiService.errorDisplay('Could not approve service key', function() {
          loadServiceKeys();
          callback(false);
        });

        var data = {
          'notes': approvalKeyInfo.notes
        };

        var params = {
          'kid': approvalKeyInfo.key.kid
        };

        ApiService.approveServiceKey(data, params).then(function(resp) {
          loadServiceKeys();
          callback(true);
        }, errorHandler);
      };
      
      $scope.updateApprovalKeyInfoNotes = function(content) {
        $scope.approvalKeyInfo.notes = content;
      };

      $scope.showCreateKey = function() {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.newKey = {
          'expiration': null
        };

        $('#createKeyModal').modal('show');
      };

      $scope.showDeleteKey = function(key) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        $scope.deleteKeyInfo = {
          'key': key
        };
      };

      $scope.deleteKey = function(deleteKeyInfo, callback) {
        if (StateService.inReadOnlyMode()) {
          return;
        }

        var errorHandler = ApiService.errorDisplay('Could not delete service key', function() {
          loadServiceKeys();
          callback(false);
        });

        var params = {
          'kid': deleteKeyInfo.key.kid
        };

        ApiService.deleteServiceKey(null, params).then(function(resp) {
          loadServiceKeys();
          callback(true);
        }, errorHandler);
      };

      $scope.isDownloadSupported = function() {
        var isSafari = /^((?!chrome).)*safari/i.test(navigator.userAgent);
        if (isSafari) {
          // Doesn't work properly in Safari, sadly.
          return false;
        }

        try { return !!new Blob(); } catch(e) {}
        return false;
      };

      $scope.downloadPrivateKey = function(key) {
        var blob = new Blob([key.private_key]);
        FileSaver.saveAs(blob, $scope.getKeyTitle(key) + '.pem');
      };

      $scope.askDeleteMultipleKeys = function(keys) {
        $scope.deleteKeysInfo = {
          'keys': keys
        };
      };

      $scope.askApproveMultipleKeys = function(keys) {
        $scope.approveKeysInfo = {
          'keys': keys
        };
      };

      $scope.askChangeExpirationMultipleKeys = function(keys) {
        $scope.changeKeysInfo = {
          'keys': keys
        };
      };

      $scope.allKeyFilter = function(key) {
        return true;
      };

      $scope.noKeyFilter = function(key) {
        return false;
      };

      $scope.unapprovedKeyFilter = function(key) {
        return !key.approval;
      };

      $scope.expiredKeyFilter = function(key) {
        return $scope.getExpirationInfo(key)['className'] == 'expired';
      };

      $scope.allRequireApproval = function(keys) {
        for (var i = 0; i < keys.length; ++i) {
          if (keys[i].approval) {
            return false;
          }
        }

        return true;
      };

      $scope.allExpired = function(keys) {
        for (var i = 0; i < keys.length; ++i) {
          if (!$scope.expiredKeyFilter(keys[i])) {
            return false;
          }
        }

        return true;
      };

      var forAllKeys = function(keys, error_msg, performer, callback) {
        var counter = 0;
        var performAction = function() {
          if (counter >= keys.length) {
            loadServiceKeys();
            callback(true);
            return;
          }

          var key = keys[counter];
          var errorHandler = function(resp) {
            if (resp.status != 404) {
              bootbox.alert(error_msg);
              loadServiceKeys();
              callback(false);
              return;
            }

            performAction();
          };

          counter++;
          performer(key).then(performAction, errorHandler);
        };

        performAction();
      };

      $scope.deleteKeys = function(info, callback) {
        var performer = function(key) {
          var params = {
            'kid': key.kid
          };

          return ApiService.deleteServiceKey(null, params);
        };

        forAllKeys(info.keys, 'Could not delete service key', performer, callback);
      };

      $scope.approveKeys = function(info, callback) {
        var performer = function(key) {
          var params = {
            'kid': key.kid
          };

          var data = {
            'notes': $scope.approveKeysInfo.notes
          };

          return ApiService.approveServiceKey(data, params);
        };

        forAllKeys(info.keys, 'Could not approve service key', performer, callback);
      };
      
      $scope.updateApproveKeysInfoNotes = function(content) {
        $scope.approveKeysInfo.notes = content;
      };
      
      $scope.changeKeysExpiration = function(info, callback) {
        var performer = function(key) {
          var data = {
            'expiration': info.expiration_date || null
          };

          var params = {
            'kid': key.kid
          };

          return ApiService.updateServiceKey(data, params);
        };

        forAllKeys(info.keys, 'Could not update service key', performer, callback);
      };

      $scope.$watch('options.filter',  buildOrderedKeys);
      $scope.$watch('options.predicate',  buildOrderedKeys);
      $scope.$watch('options.reverse',  buildOrderedKeys);

      $scope.$watch('isEnabled', function(value) {
        if (value) {
          loadServiceKeys();
        }
      });
    }
  };
  return directiveDefinitionObject;
});