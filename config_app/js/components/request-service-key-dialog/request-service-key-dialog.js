const templateUrl = require('./request-service-key-dialog.html');
/**
 * An element which displays a dialog for requesting or creating a service key.
 */
angular.module('quay-config').directive('requestServiceKeyDialog', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl,
    replace: false,
    transclude: true,
    restrict: 'C',
    scope: {
      'requestKeyInfo': '=requestKeyInfo',
      'keyCreated': '&keyCreated'
    },
    controller: function($scope, $element, $timeout, ApiService) {
      var handleNewKey = function(key) {
        var data = {
          'notes': 'Approved during setup of service ' + key.service
        };

        var params = {
          'kid': key.kid
        };

        ApiService.approveServiceKey(data, params).then(function(resp) {
          $scope.keyCreated({'key': key});
          $scope.step = 2;
        }, ApiService.errorDisplay('Could not approve service key'));
      };

      $scope.show = function() {
        $scope.working = false;
        $scope.step = 1;

        var notes = 'Created during setup for service `' + $scope.requestKeyInfo.service + '`';
        if ($scope.requestKeyInfo.newKey) {
          notes = 'Replacement key for service `' + $scope.requestKeyInfo.service + '`';
        }

        $scope.preshared = {
          'name': $scope.requestKeyInfo.service + ' Service Key',
          'notes': notes
        };

        $element.find('.modal').modal({});
      };

      $scope.hide = function() {
        $scope.loading = false;
        $element.find('.modal').modal('hide');
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
        FileSaver.saveAs(blob, key.service + '.pem');
      };

      $scope.createPresharedKey = function() {
        $scope.working = true;

        var data = {
          'name': $scope.preshared.name,
          'service': $scope.requestKeyInfo.service,
          'expiration': $scope.preshared.expiration || null,
          'notes': $scope.preshared.notes
        };

        ApiService.createServiceKey(data).then(function(resp) {
          $scope.working = false;
          $scope.step = 2;
          $scope.createdKey = resp;
          $scope.keyCreated({'key': resp});
        }, ApiService.errorDisplay('Could not create service key'));
      };
      
      $scope.updateNotes = function(content) {
        $scope.preshared.notes = content;
      };

      $scope.$watch('requestKeyInfo', function(info) {
        if (info && info.service) {
          $scope.show();
        }
      });
    }
  };
  return directiveDefinitionObject;
});