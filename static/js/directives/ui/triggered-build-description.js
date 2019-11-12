/**
 * An element which displays information about a build that was triggered from an outside source.
 */
angular.module('quay').directive('triggeredBuildDescription', function () {
  var directiveDefinitionObject = {
    priority: 0,
    templateUrl: '/static/directives/triggered-build-description.html',
    replace: false,
    transclude: false,
    restrict: 'C',
    scope: {
      'build': '=build'
    },
    controller: function($scope, $element, KeyService, TriggerService) {
      $scope.TriggerService = TriggerService;
      $scope.showLongDescription = false;

      $scope.toggleLongDescription = function() {
        $scope.showLongDescription = !$scope.showLongDescription;
      };

      $scope.hasLongDescription = function(message) {
        if (!message) { return ''; }
        return message.length >= 80 || message.split('\n').length > 1;
      };

      $scope.getMessageSummary = function(message) {
        if (!message) { return ''; }
        var lines = message.split('\n');
        return lines[0].substring(0, 79).trim();
      };

      $scope.getMessageLongDescription = function(message) {
        if (!message) { return ''; }
        var lines = message.split('\n');
        if (lines[0].length >= 80) {
          lines[0] = lines[0].substring(80);
        } else {
          lines.splice(0, 1);
        }

        return lines.join('\n').trim();
      };

      $scope.$watch('build', function(build) {
        if (!build) { return; }

        var triggerMetadata = build.trigger_metadata || {};
        if (triggerMetadata.commit_info) {
          $scope.infoDisplay = 'fullcommit';
          return;
        }

        if (!build.trigger) {
          $scope.infoDisplay = build.manual_user ? 'manual+user' : 'manual';
          return;
        }

        if (build.trigger.build_source && TriggerService.getCommitSHA(triggerMetadata)) {
          $scope.infoDisplay = 'commitsha';
          return;
        }

        $scope.infoDisplay = 'source';
      });
    }
  };
  return directiveDefinitionObject;
});
