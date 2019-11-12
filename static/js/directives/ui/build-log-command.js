/**
 * An element which displays a command in a build.
 */
angular.module('quay').directive('buildLogCommand', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/build-log-command.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'command': '<command'
    },
    controller: function($scope, $element) {
      $scope.getWithoutStep = function(fullTitle) {
        var colon = fullTitle.indexOf(':');
        if (colon <= 0) {
          return '';
        }

        return $.trim(fullTitle.substring(colon + 1));
      };

      $scope.isSecondaryFrom = function(fullTitle) {
        if (!fullTitle) { return false; }

        var command = $scope.getWithoutStep(fullTitle);
        return command.indexOf('FROM ') == 0 && fullTitle.indexOf('Step 1 ') < 0;
      };

      $scope.fromName = function(fullTitle) {
        var command = $scope.getWithoutStep(fullTitle);
        if (command.indexOf('FROM ') != 0) {
          return null;
        }

        var parts = command.split(' ');
        for (var i = 0; i < parts.length - 1; i++) {
          var part = parts[i];
          if ($.trim(part) == 'as') {
            return parts[i + 1];
          }
        }
        return null;
      }
    }
  };
  return directiveDefinitionObject;
});
