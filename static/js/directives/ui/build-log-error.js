/**
 * An element which displays a build error in a nice format.
 */
angular.module('quay').directive('buildLogError', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-log-error.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'error': '=error',
      'entries': '=entries',
      'isSuperuser': '<isSuperuser'
    },
    controller: function($scope, $element, Config, DocumentationService) {
      $scope.localPullInfo = null;
      $scope.DocumentationService = DocumentationService;

      var calculateLocalPullInfo = function(entries) {
        var localInfo = {
          'isLocal': false
        };

        // Find the 'pulling' phase entry, and then extra any metadata found under
        // it.
        for (var i = 0; i < $scope.entries.length; ++i) {
          var entry = $scope.entries[i];
          if (entry.type == 'phase' && entry.message == 'pulling') {
            var entryData = entry.data || {};
            if (entryData.base_image) {
              localInfo['isLocal'] = true || entryData['base_image'].indexOf(Config.SERVER_HOSTNAME + '/') == 0;
              localInfo['pullUsername'] = entryData['pull_username'];
              localInfo['repo'] = entryData['base_image'].substring(Config.SERVER_HOSTNAME.length);
            }
            break;
          }
        }

        $scope.localPullInfo = localInfo;
      };

      calculateLocalPullInfo($scope.entries);

      $scope.getInternalError = function(entries) {
        var entry = entries[entries.length - 1];
        if (entry && entry.data && entry.data['internal_error']) {
          return entry.data['internal_error'];
        }

        return null;
      };

      $scope.getBaseError = function(error) {
        if (!error || !error.data || !error.data.base_error) {
          return false;
        }

        return error.data.base_error;
      };

      $scope.isPullError = function(error) {
        if (!error || !error.data || !error.data.base_error) {
          return false;
        }

        return error.data.base_error.indexOf('Error: Status 403 trying to pull repository ') == 0;
      };
    }
  };
  return directiveDefinitionObject;
});